"""
================================================================================
PHASE 4 - PRODUCT DEMAND PREDICTION  (Lesson 4)
================================================================================
Goal: estimate how many units of a product will sell in a future period.
Input: historical daily sales per store & item + the target date.
Output: predicted units (e.g. "~100 units next month").

Compare TWO algorithms and keep the winner:
  Model A: Random Forest Regressor
  Model B: XGBoost Regressor

Dataset: Store Item Demand train.csv  (date, store, item, sales) - 5 years.

Preprocessing (TIME-SERIES aware -> no random shuffle!):
  1. Parse date -> year, month, day, dayofweek, weekofyear, is_weekend.
  2. Encode store, item as numeric ids.
  3. LAG features (autocorrelation): sales at t-1, t-7, t-14 (per store-item).
  4. ROLLING means: 7-day and 30-day average sales (per store-item).
  5. TIME-BASED split: train on earlier months, validate on the LAST 90 days.
     (Random split would leak future into past -> invalid for forecasting.)

Inference: given (store,item, start_date, horizon_days) we forecast forward
recursively - each day's prediction feeds the next day's lag/rolling features.
================================================================================
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb

RAW_CSV      = "data/raw/demand/train.csv"
PROCESSED_DIR = "data/processed/demand"
MODEL_DIR    = "fastapi_ml/models"
RANDOM_STATE = 42
VAL_DAYS     = 90          # last 90 days used as validation
HORIZON      = 30          # default forecast horizon (days)

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ----------------------------------------------------------------------------- #
# 1. LOAD + DATE FEATURES
# ----------------------------------------------------------------------------- #
print("[1/7] Loading demand train.csv ...")
df = pd.read_csv(RAW_CSV, parse_dates=["date"])
print(f"      rows: {len(df):,} | stores: {df['store'].nunique()} | items: {df['item'].nunique()}")
print(f"      date range: {df['date'].min().date()} -> {df['date'].max().date()}")

df = df.sort_values(["store", "item", "date"]).reset_index(drop=True)
df["year"]      = df["date"].dt.year
df["month"]     = df["date"].dt.month
df["day"]       = df["date"].dt.day
df["dayofweek"] = df["date"].dt.dayofweek
df["weekofyear"]= df["date"].dt.isocalendar().week.astype(int)
df["is_weekend"]= (df["dayofweek"] >= 5).astype(int)
df["store_id"]  = df["store"].astype("category").cat.codes
df["item_id"]   = df["item"].astype("category").cat.codes

# ----------------------------------------------------------------------------- #
# 2. LAG + ROLLING FEATURES  (per store-item, in date order)
# ----------------------------------------------------------------------------- #
print("[2/7] Engineering lag + rolling features (per store-item) ...")
g = df.groupby(["store", "item"])["sales"]
df["lag1"]  = g.shift(1)
df["lag7"]  = g.shift(7)
df["lag14"] = g.shift(14)
df["roll7"] = g.transform(lambda s: s.shift(1).rolling(7).mean())
df["roll30"]= g.transform(lambda s: s.shift(1).rolling(30).mean())

FEATURES = ["year", "month", "day", "dayofweek", "weekofyear", "is_weekend",
            "store_id", "item_id", "lag1", "lag7", "lag14", "roll7", "roll30"]
df = df.dropna(subset=FEATURES + ["sales"]).reset_index(drop=True)
print(f"      modelling rows after dropping early NaN: {len(df):,}")

# ----------------------------------------------------------------------------- #
# 3. TIME-BASED SPLIT
# ----------------------------------------------------------------------------- #
print("[3/7] Time-based split (last {} days = validation) ...".format(VAL_DAYS))
cutoff = df["date"].max() - pd.Timedelta(days=VAL_DAYS)
train = df[df["date"] < cutoff]
val   = df[df["date"] >= cutoff]
Xtr, ytr = train[FEATURES], train["sales"]
Xva, yva = val[FEATURES], val["sales"]
print(f"      train rows: {len(train):,} | val rows: {len(val):,}")

# ----------------------------------------------------------------------------- #
# 4. TRAIN + EVALUATE BOTH MODELS
# ----------------------------------------------------------------------------- #
print("[4/7] Training + evaluating Random Forest vs XGBoost ...")
def evaluate(model, X, y):
    p = model.predict(X)
    mae = mean_absolute_error(y, p)
    rmse = mean_squared_error(y, p) ** 0.5
    return mae, rmse

rf = RandomForestRegressor(n_estimators=120, n_jobs=-1, random_state=RANDOM_STATE)
rf.fit(Xtr, ytr)
mae_rf, rmse_rf = evaluate(rf, Xva, yva)

xgbm = xgb.XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1,
                        n_jobs=-1, random_state=RANDOM_STATE)
xgbm.fit(Xtr, ytr)
mae_x, rmse_x = evaluate(xgbm, Xva, yva)

print(f"\n      {'Model':<20}{'MAE':>10}{'RMSE':>10}")
print(f"      {'Random Forest':<20}{mae_rf:>10.3f}{rmse_rf:>10.3f}")
print(f"      {'XGBoost':<20}{mae_x:>10.3f}{rmse_x:>10.3f}")

# ----------------------------------------------------------------------------- #
# 5. PICK WINNER (lower RMSE; tie-break MAE)
# ----------------------------------------------------------------------------- #
winner_name, winner, w_mae, w_rmse = (
    ("XGBoost", xgbm, mae_x, rmse_x) if rmse_x <= rmse_rf else
    ("Random Forest", rf, mae_rf, rmse_rf))
print(f"\n[5/7] WINNER: {winner_name}  (MAE={w_mae:.3f}, RMSE={w_rmse:.3f})")

# top features (viva: shows what drives demand)
print("      Top features (Random Forest importance):")
imp = sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1])[:5]
for f, i in imp:
    print(f"        {f:<12} {i:.3f}")

# ----------------------------------------------------------------------------- #
# 6. REFIT WINNER ON ALL DATA
# ----------------------------------------------------------------------------- #
print("[6/7] Refitting winner on ALL data ...")
winner.fit(df[FEATURES], df["sales"])

# ----------------------------------------------------------------------------- #
# 7. SAVE WINNER + inference helper data
# ----------------------------------------------------------------------------- #
# store per-(store,item) last 30 days of sales + last date, so FastAPI can
# recursively forecast any future window.
history = {}
for (s, it), sub in df.sort_values("date").groupby(["store", "item"]):
    last30 = sub["sales"].tail(30).tolist()
    history[(int(s), int(it))] = {"sales": last30, "last_date": sub["date"].max()}

# store/item -> encoded id mapping (needed by FastAPI to build forecast features)
sc = df["store"].astype("category")
store_map = {int(k): int(v) for k, v in zip(sc.cat.categories, sc.cat.codes)}
ic = df["item"].astype("category")
item_map = {int(k): int(v) for k, v in zip(ic.cat.categories, ic.cat.codes)}

bundle = {
    "model_type": "xgboost" if winner_name == "XGBoost" else "random_forest",
    "model": winner,
    "features": FEATURES,
    "history": history,                 # (store,item) -> {sales[30], last_date}
    "store_map": store_map,
    "item_map": item_map,
    "stores": sorted(df["store"].unique().tolist()),
    "items": sorted(df["item"].unique().tolist()),
    "metrics": {"mae": w_mae, "rmse": w_rmse},
}
with open(os.path.join(MODEL_DIR, "demand_model.pkl"), "wb") as f:
    pickle.dump(bundle, f)
print(f"      saved -> {MODEL_DIR}/demand_model.pkl")

# ----------------------------------------------------------------------------- #
# DEMO: forecast next 30 days for one (store, item)
# ----------------------------------------------------------------------------- #
def forecast(store, item, start_date, horizon=HORIZON):
    key = (store, item)
    if key not in history:
        return None
    h = list(history[key]["sales"])            # rolling window (last 30)
    cur = pd.Timestamp(history[key]["last_date"]) + pd.Timedelta(days=1)
    if start_date:
        cur = pd.Timestamp(start_date)
    preds = []
    for _ in range(horizon):
        feat = {
            "year": cur.year, "month": cur.month, "day": cur.day,
            "dayofweek": cur.dayofweek,
            "weekofyear": cur.isocalendar().week,
            "is_weekend": int(cur.dayofweek >= 5),
            "store_id": df[df["store"] == store]["store_id"].iloc[0],
            "item_id": df[df["item"] == item]["item_id"].iloc[0],
            "lag1": h[-1], "lag7": h[-7], "lag14": h[-14],
            "roll7": np.mean(h[-7:]), "roll30": np.mean(h[-30:]),
        }
        x = pd.DataFrame([feat])[FEATURES]
        p = float(winner.predict(x)[0])
        p = max(p, 0.0)
        preds.append(p)
        h.append(p); h = h[-30:]              # shift window
        cur += pd.Timedelta(days=1)
    return sum(preds)

s, it = bundle["stores"][0], bundle["items"][0]
total = forecast(s, it, None, 30)
print(f"\n[7/7] Demo: store {s}, item {it} -> predicted demand next 30 days = {total:.0f} units")
print("DONE Phase 4.")
