"""
================================================================================
PHASE 2 - PRODUCT RECOMMENDATION  (Lesson 2)
================================================================================
Goal: recommend products a user (or shopper viewing an item) will like.

We compare TWO algorithms on the SAME data and keep the winner:
  Model A: Item-based COSINE SIMILARITY  (use the FULL similarity vector)
  Model B: Item-based KNN                (use only the K nearest neighbours)

Dataset: Retailrocket events.csv
  columns: timestamp, visitorid, event, itemid, transactionid
  event in {view, addtocart, transaction}

Preprocessing steps (explained inline):
  1. Keep only interaction events, drop missing ids.
  2. Weight events: view=1, addtocart=2, transaction=3 (a purchase > a view).
  3. Trim sparsity: keep top-N most-interacted items & top-M most-active users.
     -> The raw matrix is ~millions x millions and 99.9% empty; unusable as-is.
  4. Aggregate (user, item) -> total interaction weight.
  5. Time-based hold-out: for each user, hide their MOST RECENT interaction as the
     test item (so we never "predict" something they already did in training).
  6. Build the user-item matrix R (users x items), and the item-item matrix.
  7. Item-item COSINE similarity between item vectors (each item = a user-vector).
================================================================================
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# ----------------------------------------------------------------------------- #
# 0. CONFIG  (change these to experiment -> great for viva "what if" questions)
# ----------------------------------------------------------------------------- #
RAW_EVENTS   = "data/raw/recommendation/events.csv"
PROCESSED_DIR = "data/processed/recommendation"
MODEL_DIR    = "fastapi_ml/models"
TOP_ITEMS    = 600      # keep the 600 most-interacted products
TOP_USERS    = 1500     # keep the 1500 most-active shoppers
KNN_K        = 20       # KNN uses only the 20 nearest items per product
K            = 5         # we recommend a top-5 list -> evaluate Precision@5/Recall@5

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
np.random.seed(42)   # reproducible results for the viva demo

# ----------------------------------------------------------------------------- #
# 1 & 2. LOAD + WEIGHT EVENTS
# ----------------------------------------------------------------------------- #
print("[1/7] Loading events.csv ...")
df = pd.read_csv(RAW_EVENTS)
print(f"      raw rows: {len(df):,}")

# keep only the 3 interaction types we care about; drop rows missing ids
df = df.dropna(subset=["itemid", "visitorid"])
df = df[df["event"].isin(["view", "addtocart", "transaction"])]

# map each event type to a strength weight
WEIGHTS = {"view": 1, "addtocart": 2, "transaction": 3}
df["w"] = df["event"].map(WEIGHTS)

# ----------------------------------------------------------------------------- #
# 3. TRIM SPARSITY
# ----------------------------------------------------------------------------- #
print("[2/7] Trimming sparsity (top items / top users) ...")
top_items = df.groupby("itemid")["w"].sum().sort_values(ascending=False).head(TOP_ITEMS).index
top_users = df.groupby("visitorid")["w"].sum().sort_values(ascending=False).head(TOP_USERS).index
df = df[df["itemid"].isin(top_items) & df["visitorid"].isin(top_users)]
print(f"      kept rows: {len(df):,}  | items: {df['itemid'].nunique()} | users: {df['visitorid'].nunique()}")

# ----------------------------------------------------------------------------- #
# 4. AGGREGATE TO USER-ITEM WEIGHTS
# ----------------------------------------------------------------------------- #
agg = df.groupby(["visitorid", "itemid"])["w"].sum().reset_index()

# ----------------------------------------------------------------------------- #
# 5. TIME-BASED HOLD-OUT (per user, hide most recent interaction)
# ----------------------------------------------------------------------------- #
print("[3/7] Building time-based hold-out ...")
df_sorted = df.sort_values("timestamp")
holdout = df_sorted.groupby("visitorid").tail(1)[["visitorid", "itemid"]].copy()
holdout_set = set(map(tuple, holdout.values))

# train weights = every interaction EXCEPT the held-out one
train = agg[~agg.apply(lambda r: (r["visitorid"], r["itemid"]) in holdout_set, axis=1)]

# ----------------------------------------------------------------------------- #
# 6. BUILD MATRICES + INDEX MAPS
# ----------------------------------------------------------------------------- #
print("[4/7] Building user-item matrix R ...")
users = sorted(train["visitorid"].unique())
items = sorted(train["itemid"].unique())
u2i = {u: i for i, u in enumerate(users)}      # visitorid -> matrix row
i2u = {i: u for u, i in u2i.items()}
i2idx = {it: i for i, it in enumerate(items)}  # itemid   -> matrix col
idx2i = {i: it for it, i in i2idx.items()}
nU, nI = len(users), len(items)

R = np.zeros((nU, nI))
for row in train.itertuples():
    R[u2i[row.visitorid], i2idx[row.itemid]] = row.w

# item-item matrix: each ROW is one item, described by which users interacted
item_mat = R.T                                   # shape (nI, nU)
print(f"      R shape: {R.shape}  (users x items)")

# ----------------------------------------------------------------------------- #
# 7. COSINE SIMILARITY (item x item)
# ----------------------------------------------------------------------------- #
print("[5/7] Computing cosine similarity between items ...")
sim = cosine_similarity(item_mat)                # (nI, nI)
np.fill_diagonal(sim, 0.0)                       # an item is not its own neighbour

# KNN variant: keep ONLY the K most similar items per item (sparser, local)
sim_knn = np.zeros_like(sim)
for i in range(nI):
    topk = np.argsort(sim[i])[::-1][:KNN_K]
    sim_knn[i, topk] = sim[i, topk]

# ----------------------------------------------------------------------------- #
# EVALUATION  (Precision@5, Recall@5 over held-out interactions)
# ----------------------------------------------------------------------------- #
print("[6/7] Evaluating both models on held-out interactions ...")
# pre-compute each user's liked items (from TRAIN) for scoring
liked_idx = {}
for u_idx in range(nU):
    idxs = np.where(R[u_idx] > 0)[0]
    if len(idxs) > 0:
        liked_idx[u_idx] = idxs

def evaluate(sim_matrix):
    hits = 0
    denom = 0
    for r in holdout.itertuples():
        uid, iid = r.visitorid, r.itemid
        if uid not in u2i:
            continue
        u_idx = u2i[uid]
        if u_idx not in liked_idx:      # user has no train signal -> skip
            continue
        true_idx = i2idx.get(iid)
        if true_idx is None:            # held-out item was trimmed -> skip
            continue
        # score every item = weighted sum of similarity to liked items
        scores = np.zeros(nI)
        for l in liked_idx[u_idx]:
            scores += sim_matrix[:, l] * R[u_idx, l]
        scores[liked_idx[u_idx]] = -np.inf   # never recommend what they already have
        preds = np.argsort(scores)[::-1][:K]
        if true_idx in preds:
            hits += 1
        denom += 1
    prec = hits / denom if denom else 0.0
    rec = hits / denom if denom else 0.0      # 1 held-out item/user -> recall == hit rate
    return prec, rec, denom

prec_cos, rec_cos, n = evaluate(sim)
prec_knn, rec_knn, _ = evaluate(sim_knn)

print(f"\n      Evaluated on {n} users with a held-out interaction")
print(f"      {'Model':<22}{'Precision@5':>14}{'Recall@5':>12}")
print(f"      {'Cosine similarity':<22}{prec_cos:>14.4f}{rec_cos:>12.4f}")
print(f"      {'KNN (k={KNN_K})':<22}{prec_knn:>14.4f}{rec_knn:>12.4f}")

# ----------------------------------------------------------------------------- #
# PICK WINNER  (higher Precision@5 wins; tie-break on Recall)
# ----------------------------------------------------------------------------- #
winner_name = "Cosine similarity" if prec_cos >= prec_knn else f"KNN (k={KNN_K})"
winner_sim = sim if prec_cos >= prec_knn else sim_knn
print(f"\n[7/7] WINNER: {winner_name}")

# ----------------------------------------------------------------------------- #
# SAVE WINNER  (what FastAPI will load later)
# ----------------------------------------------------------------------------- #
model_bundle = {
    "model_type": "cosine" if prec_cos >= prec_knn else "knn",
    "sim_matrix": winner_sim,          # (nI, nI) item-item similarity
    "R": R,                            # user-item matrix (for user-based recs)
    "idx2item": idx2i,                # matrix col -> real itemid
    "item2idx": i2idx,                # real itemid -> matrix col
    "u2i": u2i, "i2u": i2u,
    "top_items": list(items),
    "metrics": {"precision@5": max(prec_cos, prec_knn),
                "recall@5": max(rec_cos, rec_knn)},
}
with open(os.path.join(MODEL_DIR, "recommendation_model.pkl"), "wb") as f:
    pickle.dump(model_bundle, f)
print(f"      saved -> {MODEL_DIR}/recommendation_model.pkl")

# also persist the cleaned interaction matrix for reference / later phases
np.save(os.path.join(PROCESSED_DIR, "user_item_matrix.npy"), R)
pd.DataFrame(items, columns=["itemid"]).to_csv(os.path.join(PROCESSED_DIR, "items.csv"), index=False)
print(f"      cleaned artifacts -> {PROCESSED_DIR}/")
print("\nDONE Phase 2.")
