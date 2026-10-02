"""
================================================================================
PHASE 5 - FASTAPI ML SERVICE  (the brain that serves our 3 trained models)
================================================================================
This tiny web service loads the 3 winner ".pkl" files produced in Phases 2-4 and
exposes them over HTTP so the Django website (Phase 6/7) can call them.

WHY a separate service?
  - Separation of concerns: Django = web/auth/UI, FastAPI = ML inference.
  - Each can be deployed/scaled independently.
  - Django talks to it with the `requests` library (see Phase 7).

ENDPOINTS
  GET  /health     -> are all 3 models loaded? returns their metrics.
  POST /recommend  -> item-based or user-based collaborative filtering.
  POST /sentiment   -> Positive / Neutral / Negative for a review text.
  POST /demand      -> forecast units sold for (store, item) over N days.

MODELS LOADED (from ./models/*.pkl)
  recommendation_model.pkl : cosine item-item similarity matrix (winner over KNN)
  sentiment_model.pkl      : TF-IDF + Logistic Regression (class-weight balanced)
  demand_model.pkl         : XGBoost on lag/rolling features (winner over RF)
================================================================================
"""

import os
import pickle
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------- #
# Paths: models live in ./models/ relative to this file.
# ----------------------------------------------------------------------------- #
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# These will be filled in at startup (see lifespan below).
STATE = {
    "rec": None,      # recommendation bundle
    "sent": None,     # sentiment bundle
    "dem": None,      # demand bundle
}


# ----------------------------------------------------------------------------- #
# STARTUP: load all 3 pickles ONCE, keep them in memory (fast inference).
# ----------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] loading ML models ...")
    try:
        with open(os.path.join(MODELS_DIR, "recommendation_model.pkl"), "rb") as f:
            STATE["rec"] = pickle.load(f)
        print("  - recommendation model loaded:", STATE["rec"]["model_type"])
    except Exception as e:
        print("  ! recommendation model FAILED:", e)

    try:
        with open(os.path.join(MODELS_DIR, "sentiment_model.pkl"), "rb") as f:
            STATE["sent"] = pickle.load(f)
        print("  - sentiment model loaded:", STATE["sent"]["model_type"])
    except Exception as e:
        print("  ! sentiment model FAILED:", e)

    try:
        with open(os.path.join(MODELS_DIR, "demand_model.pkl"), "rb") as f:
            STATE["dem"] = pickle.load(f)
        print("  - demand model loaded:", STATE["dem"]["model_type"])
    except Exception as e:
        print("  ! demand model FAILED:", e)

    yield
    # (nothing special to clean up on shutdown)


app = FastAPI(title="E-Commerce ML Service", version="1.0", lifespan=lifespan)


# ============================================================================= #
# REQUEST SCHEMAS (Pydantic validates incoming JSON for us)
# ============================================================================= #
class RecommendRequest(BaseModel):
    visitorid: int | None = Field(None, description="shopper id (user-based recs)")
    itemid: int | None = Field(None, description="product id (item-based recs)")
    k: int = Field(5, ge=1, le=50,
                   description="how many items to return (a caller may request a "
                               "deep candidate pool and re-rank client-side)")


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, description="review text to classify")


class DemandRequest(BaseModel):
    store: int = Field(..., description="store id (1-10)")
    item: int = Field(..., description="item id (1-50)")
    start_date: str | None = Field(None, description="YYYY-MM-DD (optional)")
    horizon: int = Field(30, ge=1, le=90, description="days to forecast")


# ============================================================================= #
# HEALTH CHECK
# ============================================================================= #
@app.get("/health")
def health():
    rec = STATE["rec"]
    sent = STATE["sent"]
    dem = STATE["dem"]
    return {
        "status": "ok" if all([rec, sent, dem]) else "degraded",
        "models": {
            "recommendation": {
                "loaded": rec is not None,
                "type": rec["model_type"] if rec else None,
                "metrics": rec.get("metrics") if rec else None,
            },
            "sentiment": {
                "loaded": sent is not None,
                "type": sent["model_type"] if sent else None,
                "metrics": sent.get("metrics") if sent else None,
            },
            "demand": {
                "loaded": dem is not None,
                "type": dem["model_type"] if dem else None,
                "metrics": dem.get("metrics") if dem else None,
            },
        },
    }


# ============================================================================= #
# ENDPOINT 1: RECOMMENDATIONS
# -----------------------------------------------------------------------------
# Two collaborative-filtering modes share ONE similarity matrix:
#   * itemid given  -> ITEM-based: "users who liked this also liked..."
#   * visitorid given -> USER-based: score every item by similarity to what the
#                         user already interacted with (weighted by strength).
#   * nothing given -> fallback: globally most-interacted items (popular list).
# ============================================================================= #
@app.post("/recommend")
def recommend(req: RecommendRequest):
    rec = STATE["rec"]
    if rec is None:
        raise HTTPException(503, "recommendation model not loaded")

    sim = rec["sim_matrix"]
    item2idx = rec["item2idx"]
    idx2item = rec["idx2item"]
    R = rec["R"]
    u2i = rec["u2i"]
    top_items = rec["top_items"]
    nI = sim.shape[0]

    results = []

    # ---- ITEM-BASED (most common on a product page: "you may also like") ----
    if req.itemid is not None:
        if req.itemid not in item2idx:
            # unknown product -> return popular fallback
            return {"mode": "item", "itemid": req.itemid,
                    "note": "unknown item, showing popular",
                    "items": [{"itemid": int(it), "score": None} for it in top_items[:req.k]]}
        idx = item2idx[req.itemid]
        scores = sim[idx].copy()
        scores[idx] = -np.inf           # never recommend the item itself
        top = np.argsort(scores)[::-1][: req.k]
        results = [{"itemid": int(idx2item[j]), "score": round(float(scores[j]), 4)}
                   for j in top if scores[j] > 0]

    # ---- USER-BASED (home page personalization) ----
    elif req.visitorid is not None:
        if req.visitorid not in u2i:
            # cold / unknown user -> popular fallback
            return {"mode": "user", "visitorid": req.visitorid,
                    "note": "unknown user, showing popular",
                    "items": [{"itemid": int(it), "score": None} for it in top_items[:req.k]]}
        u_idx = u2i[req.visitorid]
        liked = np.where(R[u_idx] > 0)[0]          # columns this user interacted with
        if len(liked) == 0:
            return {"mode": "user", "visitorid": req.visitorid,
                    "note": "no history, showing popular",
                    "items": [{"itemid": int(it), "score": None} for it in top_items[:req.k]]}
        scores = np.zeros(nI)
        for l in liked:
            scores += sim[:, l] * R[u_idx, l]      # weight by interaction strength
        scores[liked] = -np.inf
        top = np.argsort(scores)[::-1][: req.k]
        results = [{"itemid": int(idx2item[j]), "score": round(float(scores[j]), 4)}
                   for j in top if scores[j] > 0]

    # ---- FALLBACK: popular ----
    else:
        results = [{"itemid": int(it), "score": None} for it in top_items[: req.k]]

    return {"mode": "item" if req.itemid is not None else
                   ("user" if req.visitorid is not None else "popular"),
            "items": results}


# ============================================================================= #
# ENDPOINT 2: SENTIMENT
# -----------------------------------------------------------------------------
# Pipeline: text -> TF-IDF vectorizer -> classifier -> label.
# We also return a confidence score when the classifier supports probabilities
# (LogisticRegression does via predict_proba).
# ============================================================================= #
@app.post("/sentiment")
def sentiment(req: SentimentRequest):
    sent = STATE["sent"]
    if sent is None:
        raise HTTPException(503, "sentiment model not loaded")

    vec = sent["vectorizer"]
    clf = sent["classifier"]
    labels = sent["label_names"]            # ["negative","neutral","positive"]

    X = vec.transform([req.text])
    pred_idx = int(clf.predict(X)[0])

    # confidence: prefer predict_proba; fall back to softmax of decision_function
    try:
        probs = clf.predict_proba(X)[0]
        conf = float(probs[pred_idx])
    except AttributeError:
        d = clf.decision_function(X)[0]
        probs = np.exp(d - d.max()) / np.exp(d - d.max()).sum()
        conf = float(probs[pred_idx])

    return {
        "text": req.text,
        "label": labels[pred_idx],
        "label_index": pred_idx,
        "confidence": round(conf, 4),
        "all_scores": {labels[i]: round(float(probs[i]), 4) for i in range(len(labels))},
    }


# ============================================================================= #
# ENDPOINT 3: DEMAND FORECAST
# -----------------------------------------------------------------------------
# Recursive one-day-at-a-time forecasting: each predicted day becomes the lag/roll
# feature for the next day (the exact logic validated in train_demand.py).
# store_map / item_map map the real (store,item) ids -> the encoded ids the
# XGBoost model was trained on.
# ============================================================================= #
@app.post("/demand")
def demand(req: DemandRequest):
    dem = STATE["dem"]
    if dem is None:
        raise HTTPException(503, "demand model not loaded")

    model = dem["model"]
    FEATURES = dem["features"]
    history = dem["history"]
    store_map = dem["store_map"]
    item_map = dem["item_map"]

    key = (req.store, req.item)
    if key not in history:
        raise HTTPException(404, f"no sales history for store={req.store}, item={req.item}")
    if req.store not in store_map or req.item not in item_map:
        raise HTTPException(404, "store/item id not in trained encoding")

    h = list(history[key]["sales"])                       # last 30 days of sales
    cur = pd.Timestamp(history[key]["last_date"]) + pd.Timedelta(days=1)
    if req.start_date:
        cur = pd.Timestamp(req.start_date)

    daily = []
    for _ in range(req.horizon):
        feat = {
            "year": cur.year, "month": cur.month, "day": cur.day,
            "dayofweek": cur.dayofweek,
            "weekofyear": int(cur.isocalendar().week),
            "is_weekend": int(cur.dayofweek >= 5),
            "store_id": store_map[req.store],
            "item_id": item_map[req.item],
            "lag1": h[-1], "lag7": h[-7], "lag14": h[-14],
            "roll7": float(np.mean(h[-7:])), "roll30": float(np.mean(h[-30:])),
        }
        x = pd.DataFrame([feat])[FEATURES]
        p = max(float(model.predict(x)[0]), 0.0)
        daily.append(round(p, 2))
        h.append(p)
        h = h[-30:]                                       # keep the rolling window
        cur += pd.Timedelta(days=1)

    return {
        "store": req.store,
        "item": req.item,
        "horizon_days": req.horizon,
        "start_date": str(cur - pd.Timedelta(days=req.horizon))[:10],
        "end_date": str(cur - pd.Timedelta(days=1))[:10],
        "predicted_total_units": round(sum(daily), 1),
        "predicted_daily_units": daily,
    }


# ============================================================================= #
# Run locally:  uvicorn main:app --reload --port 8000
# ============================================================================= #
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
