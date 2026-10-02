"""
Seed the catalog. We link each Product.ml_item_id to a REAL item id from the
recommendation dataset (Retailrocket) so that "You may also like" (FastAPI
/recommend) returns ids that actually map back to products in our store.
Run:  python seed.py
"""
import os
import pickle
import random

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")
django.setup()

from products.models import Category, Product

PKL = os.path.join(os.path.dirname(__file__), "..", "fastapi_ml", "models", "recommendation_model.pkl")
rec = pickle.load(open(PKL, "rb"))
top_items = rec["top_items"]            # real dataset item ids, most-interacted first

CATS = ["Skincare", "Makeup", "Haircare", "Fragrance", "Body"]
cat_objs = {}
for c in CATS:
    cat_objs[c], _ = Category.objects.get_or_create(name=c, defaults={"slug": c.lower()})

ADJ = ["Velvet", "Rose", "Aqua", "Pure", "Golden", "Soft", "Calm", "Lumen",
       "Silk", "Dewy", "Bare", "Noir", "Bloom", "Cedar", "Aura", "Mist"]
NOUN = ["Serum", "Cream", "Toner", "Mist", "Oil", "Balm", "Glow", "Mask",
        "Essence", "Scrub", "Lotion", "Eau de Parfum"]
ACCENTS = ["#d8c3b3", "#e7c9c0", "#cbb9a6", "#e3d2c0", "#d6b9a8", "#c8a99a"]

# We seed the FULL recommendation pool (all 600 items) so every item-based
# recommendation returned by the ML service maps back to a real product.
N = len(top_items)
created = 0
for i in range(N):
    ml_id = int(top_items[i])
    if Product.objects.filter(ml_item_id=ml_id).exists():
        continue
    name = f"{random.choice(ADJ)} {random.choice(NOUN)} {i+1:03d}"
    cat = cat_objs[CATS[i % len(CATS)]]
    Product.objects.create(
        ml_item_id=ml_id,
        name=name,
        category=cat,
        price=round(random.uniform(350, 3200), 0),
        description=f"A thoughtful {cat.name.lower()} essential by Lumina. "
                    f"Gentle, effective, and made to be part of your daily ritual.",
        rating=round(random.uniform(3.4, 5.0), 1),
        stock=random.randint(5, 80),
        accent=random.choice(ACCENTS),
    )
    created += 1

print(f"Seeded {created} products across {len(CATS)} categories.")
