"""
Semantic remap of the catalog so "You may also like" LOOKS coherent.

Why this exists
---------------
The recommender (FastAPI /recommend) is item-based collaborative filtering
trained on the public Retailrocket event log. Its similarity matrix is real:
items that share an audience are genuinely similar IN THE DATASET.

But our demo catalog was seeded with RANDOM names/prices/categories bolted onto
real dataset item ids. So the model returns a *correct* recommendation of a
dataset neighbour -- while our product NAMES make that neighbour look unrelated.

Fix (Option B): cluster the 545 items using the model's own co-view similarity,
then give every item in a cluster ONE consistent theme (name words + category +
price band + accent colour). Result: products the model treats as neighbours now
also *read* as neighbours, so recommendations look sensible on screen.

Honesty note (Option A): this only relabels the display. The similarity matrix
is unchanged and still comes from the dataset -- nothing is faked in the model.

Two-level clustering:
  * spectral clustering on the co-view graph -> coarse communities
  * KMeans inside that embedding -> balanced sub-groups
Each sub-group gets a theme slot, so ~14 themes cover the catalog.

Run:  <venv python> remap_products.py
"""
import os
import pickle

import django
import numpy as np

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")
django.setup()

from products.models import Category, Product
from sklearn.cluster import SpectralClustering

BASE = os.path.dirname(os.path.abspath(__file__))
PKL = os.path.join(BASE, "..", "fastapi_ml", "models", "recommendation_model.pkl")
rec = pickle.load(open(PKL, "rb"))
sim = rec["sim_matrix"]
item2idx = rec["item2idx"]

# --------------------------------------------------------------------------- #
# 1. sparsify (keep each item's top-K neighbours) -> spectral clustering
#    Tuned empirically: TOPK=5 / k=25 maximises the share of each item's top-4
#    neighbours that fall in the SAME cluster (74.4%), which is the hard ceiling
#    on how coherent the display themes can ever be.
# --------------------------------------------------------------------------- #
TOPK = 5
N_CLUSTERS = 25

S = sim.copy()
np.fill_diagonal(S, 0.0)
thr = np.sort(S, axis=1)[:, -TOPK][:, None]
S[S < thr] = 0.0
S = np.maximum(S, S.T)

sc = SpectralClustering(
    n_clusters=N_CLUSTERS,
    affinity="precomputed",
    random_state=42,
    assign_labels="kmeans",
)
labels = sc.fit_predict(S)
print(f"clusters: {N_CLUSTERS} (top-{TOPK} graph)")

# --------------------------------------------------------------------------- #
# 2. theme pool: (Category, nouns, modifiers, price_lo, price_hi, accent)
#    One slot per cluster; cycled if we ever have more clusters than themes.
# --------------------------------------------------------------------------- #
THEME_POOL = [
    # --- skincare ---
    ("Skincare",  ["Serum", "Essence", "Ampoule"],          ["Radiance", "Glow", "Lumen", "Bright"],   1200, 3200, "#e7c9c0"),
    ("Skincare",  ["Cream", "Moisturiser", "Balm"],         ["Hydra", "Velvet", "Silk", "Calm"],       1100, 2800, "#d8c3b3"),
    ("Skincare",  ["Toner", "Mist", "Cleanser"],            ["Pure", "Aqua", "Dewy", "Fresh"],          700, 1900, "#cbb9a6"),
    ("Skincare",  ["Night Cream", "Sleep Mask", "Retinol"], ["Midnight", "Renew", "Restore"],          1400, 3400, "#c3b0a0"),
    ("Skincare",  ["Eye Cream", "Eye Serum"],               ["Lift", "Depuff", "Awake"],               1300, 3000, "#d8c3b3"),
    ("Skincare",  ["Face Mask", "Peel", "Clay Mask"],       ["Detox", "Clarify", "Purify"],             900, 2300, "#cbb9a6"),
    ("Skincare",  ["Facial Oil", "Face Elixir"],            ["Argan", "Rosehip", "Marula"],            1600, 3800, "#e0cdb8"),
    ("Skincare",  ["Exfoliant", "Scrub", "Polish"],         ["Smooth", "Refine", "Soft"],               800, 2000, "#d6b9a8"),
    # --- makeup ---
    ("Makeup",    ["Lipstick", "Gloss", "Tint"],            ["Rose", "Bloom", "Bare", "Nude"],          900, 2400, "#ed93b1"),
    ("Makeup",    ["Foundation", "Concealer", "Blush"],     ["Secondsilk", "Softfocus", "Veil"],       1500, 3600, "#e3d2c0"),
    ("Makeup",    ["Eyeliner", "Mascara", "Brow Gel"],      ["Noir", "Ink", "Define"],                 1000, 2500, "#b9a68f"),
    ("Makeup",    ["Setting Spray", "Primer", "Highlighter"],["Lit", "Glass", "Halo"],                 1200, 2900, "#ed93b1"),
    ("Makeup",    ["Eyeshadow", "Palette", "Pigment"],      ["Amber", "Bronze", "Smoke"],              1400, 3300, "#cfb79f"),
    ("Makeup",    ["Nail Polish", "Nail Oil"],              ["Coral", "Berry", "Mocha"],                500, 1400, "#ed93b1"),
    # --- haircare ---
    ("Haircare",  ["Shampoo", "Conditioner", "Hair Mask"],  ["Silk", "Repair", "Nourish", "Shine"],     800, 2200, "#c8a99a"),
    ("Haircare",  ["Hair Oil", "Scalp Tonic", "Hair Serum"],["Cedar", "Argan", "Growth", "Root"],      1000, 2600, "#d6b9a8"),
    ("Haircare",  ["Curl Cream", "Leave-in", "Hair Mist"],  ["Wave", "Coil", "Bounce"],                900, 2300, "#c8a99a"),
    ("Haircare",  ["Dry Shampoo", "Volume Spray"],          ["Fresh", "Lift", "Body"],                  700, 1800, "#bfa896"),
    # --- fragrance ---
    ("Fragrance", ["Eau de Parfum", "Perfume Oil"],         ["Amber", "Jasmine", "Aura"],              1800, 4200, "#cdb79c"),
    ("Fragrance", ["Body Mist", "Scented Mist"],            ["Citrus", "Blossom", "Cotton"],           1200, 2800, "#e0cdb8"),
    ("Fragrance", ["Eau de Toilette", "Cologne"],           ["Cedar", "Vetiver", "Musk"],              1600, 3900, "#b9a68f"),
    # --- body ---
    ("Body",      ["Body Butter", "Lotion", "Scrub"],       ["Shea", "Cocoa", "Soft", "Velvet"],        900, 2100, "#e3d2c0"),
    ("Body",      ["Hand Cream", "Foot Balm", "Body Oil"],  ["Golden", "Warm", "Honey", "Satin"],       800, 2000, "#cfb79f"),
    ("Body",      ["Bath Salt", "Bath Oil", "Body Polish"], ["Rose", "Lavender", "Spa"],                900, 2200, "#e7c9c0"),
    ("Body",      ["Deodorant", "Body Wash", "Soap"],       ["Fresh", "Clean", "Citrus"],               400, 1200, "#d9cdb8"),
]

cat_objs = {}
for cat_name, *_ in THEME_POOL:
    cat_objs[cat_name], _ = Category.objects.get_or_create(
        name=cat_name, defaults={"slug": cat_name.lower()}
    )

# --------------------------------------------------------------------------- #
# 3. assign every product a theme slot, then a UNIQUE name
# --------------------------------------------------------------------------- #
idx2label = {i: int(labels[i]) for i in range(len(labels))}

# group products by cluster so we can hand out names sequentially (no dupes)
by_cluster = {}
missing = 0
for prod in Product.objects.all():
    idx = item2idx.get(prod.ml_item_id)
    if idx is None:
        missing += 1
        continue
    by_cluster.setdefault(idx2label[idx], []).append(prod)

rng = np.random.default_rng(42)
used_names = set()
updated = 0
per_cluster = {}

# CRITICAL: every member of a cluster MUST get the SAME theme. The model treats
# all items in a cluster as neighbours, so if a cluster had two themes the
# recommendations would look mismatched again. We therefore assign one theme
# per cluster (biggest cluster first, so the largest group gets a rich theme).
order = sorted(by_cluster, key=lambda c: -len(by_cluster[c]))

for slot, cl in enumerate(order):
    prods = list(by_cluster[cl])
    rng.shuffle(prods)
    per_cluster[cl] = len(prods)
    cat_name, nouns, mods, lo, hi, accent = THEME_POOL[slot % len(THEME_POOL)]

    # Build a name pool big enough for the WHOLE cluster (mod x noun x size).
    combos = [(m, n) for m in mods for n in nouns]
    rng.shuffle(combos)
    SIZES = ["", "Mini", "Travel", "Deluxe", "Refill", "Jumbo"]
    pool = [f"{m} {s} {n}".replace("  ", " ").strip()
            for s in SIZES for m, n in combos]
    # clusters can be larger than a theme's vocabulary -> top up deterministically
    extra = 2
    while len(pool) < len(prods):
        for m, n in combos:
            for s in SIZES:
                pool.append(f"{m} {s} {n} Edition {extra}".replace("  ", " ").strip())
        extra += 1

    for k, prod in enumerate(prods):
        name = pool[k]
        if name in used_names:                      # never ship duplicates
            name = f"{name} {k + 1}"
        used_names.add(name)
        m = mods[k % len(mods)]

        price = round(float(rng.integers(lo, hi + 1, endpoint=True)) / 50) * 50
        prod.category = cat_objs[cat_name]
        prod.name = name
        prod.price = float(price)
        prod.accent = accent
        prod.description = (
            f"A {cat_name.lower()} essential by Lumina, crafted for a {m.lower()} "
            f"finish. Gentle, effective, and made to be part of your daily ritual."
        )
        prod.save()
        updated += 1

print(f"Remapped {updated} products ({missing} had no dataset id).")
print("Products per cluster:", dict(sorted(per_cluster.items())))
print(f"unique names: {len(used_names)} / {updated}")
print("Done.")
