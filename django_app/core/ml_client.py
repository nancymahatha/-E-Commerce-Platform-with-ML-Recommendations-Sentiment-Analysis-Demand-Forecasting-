"""
Thin client that calls our FastAPI ML service (Phase 5).
Each function returns the parsed JSON, or None if the service is unreachable
so the UI can degrade gracefully (e.g. hide recommendations) instead of crashing.
"""
import requests
from django.conf import settings


def _post(path, payload, timeout=12):
    try:
        r = requests.post(
            settings.ML_API_BASE + path,
            json=payload,
            proxies={"http": None, "https": None},   # avoid corporate proxy on localhost
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def _get(path, timeout=12):
    """GET helper (used for /health). Returns parsed JSON or None."""
    try:
        r = requests.get(
            settings.ML_API_BASE + path,
            proxies={"http": None, "https": None},
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def ml_health():
    """Live status + evaluation metrics of the 3 ML models, or None if down."""
    return _get("/health")


def recommend_by_item(item_id, k=4):
    """Item-based: 'users who viewed this also viewed...'."""
    return _post("/recommend", {"itemid": int(item_id), "k": k})


def recommend_popular(k=8):
    """Fallback: globally most-interacted items."""
    return _post("/recommend", {"k": k})


def analyze_sentiment(text):
    """Return {'label':..., 'confidence':...} or None."""
    return _post("/sentiment", {"text": text})


def forecast_demand(store, item, horizon=30):
    """Return forecast dict or None."""
    return _post("/demand", {"store": int(store), "item": int(item), "horizon": horizon})


# --------------------------------------------------------------------------- #
# Local read-only access to the trained recommender's interaction matrix.
#
# The FastAPI service exposes /recommend (scores only). To re-rank its output on
# real evidence we also need the raw user-item matrix R, which lives inside the
# same pickle. We load it ONCE, lazily, and keep it in memory.
#
# This is read-only: we never retrain or modify the model.
# --------------------------------------------------------------------------- #
_R_CACHE = {"R": None, "item2idx": None}


def _load_matrix():
    """Load {R, item2idx} from the recommendation pickle (cached)."""
    if _R_CACHE["R"] is None:
        import os
        import pickle

        base = getattr(settings, "BASE_DIR", None)
        candidates = []
        if base:
            candidates.append(os.path.join(base, "..", "fastapi_ml", "models",
                                           "recommendation_model.pkl"))
            candidates.append(os.path.join(base, "fastapi_ml", "models",
                                           "recommendation_model.pkl"))
        for path in candidates:
            if os.path.exists(path):
                rec = pickle.load(open(path, "rb"))
                _R_CACHE["R"] = rec["R"]
                _R_CACHE["item2idx"] = rec["item2idx"]
                break
    return _R_CACHE["R"], _R_CACHE["item2idx"]


def _co_view_counts(item_id, candidate_ids):
    """How many shoppers interacted with `item_id` AND each candidate.

    Returns {candidate_itemid: shared_viewer_count}. Empty dict on any problem,
    so callers degrade gracefully.
    """
    try:
        R, item2idx = _load_matrix()
        if R is None:
            return {}
        import numpy as np

        i = item2idx.get(int(item_id))
        if i is None:
            return {}
        col_i = R[:, i] > 0
        out = {}
        for cid in candidate_ids:
            j = item2idx.get(int(cid))
            if j is None:
                continue
            out[int(cid)] = int(np.sum(col_i & (R[:, j] > 0)))
        return out
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# Read-only access to the demand model's stored sales history.
#
# The XGBoost demand model predicts the next 30 days from the PREVIOUS 30 days
# of real sales (plus day-of-week / month / lag / rolling-mean features). The
# FastAPI /demand endpoint returns only the forecast; to EXPLAIN the basis we
# also read the raw recent sales window that the model started from.
#
# Loaded lazily & cached. Read-only — the model is never modified.
# --------------------------------------------------------------------------- #
_DEMAND_CACHE = {"history": None}


def _load_demand_history_map():
    """Load { (store,item): {'sales': [...30], 'last_date': ts} } from the pickle."""
    if _DEMAND_CACHE["history"] is None:
        import os
        import pickle

        base = getattr(settings, "BASE_DIR", None)
        candidates = []
        if base:
            candidates.append(os.path.join(base, "..", "fastapi_ml", "models",
                                           "demand_model.pkl"))
            candidates.append(os.path.join(base, "fastapi_ml", "models",
                                           "demand_model.pkl"))
        _DEMAND_CACHE["history"] = {}
        for path in candidates:
            if os.path.exists(path):
                dem = pickle.load(open(path, "rb"))
                _DEMAND_CACHE["history"] = dem.get("history", {})
                break
    return _DEMAND_CACHE["history"]


def demand_history(store, item):
    """Return the recent sales window behind a forecast, for the 'why' panel.

    Returns {'sales': [...], 'labels': [...], 'last_date': str} or None.
    """
    try:
        key = (int(store), int(item))
        hist = _load_demand_history_map().get(key)
        if not hist:
            return None
        sales = list(hist.get("sales", []))
        last = hist.get("last_date")
        # build human date labels ending at last_date
        labels = []
        try:
            import pandas as pd
            end = pd.Timestamp(last)
            start = end - pd.Timedelta(days=len(sales) - 1)
            labels = [(start + pd.Timedelta(days=d)).strftime("%b %d")
                      for d in range(len(sales))]
        except Exception:
            labels = []
        return {
            "sales": sales,
            "labels": labels,
            "last_date": str(last)[:10] if last is not None else None,
        }
    except Exception:
        return None
