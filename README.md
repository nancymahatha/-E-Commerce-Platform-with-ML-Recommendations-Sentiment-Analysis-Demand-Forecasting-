# E-Commerce ML Platform

A full-stack e-commerce site (Django + SQLite) powered by three ML models served
through a FastAPI microservice. Built for an academic viva: every layer
(dataset → preprocessing → training → serving → UI) is reproducible and explained.

## Features
- **Product recommendation** — item-based cosine similarity (Collaborative Filtering).
- **Review sentiment** — 3-class (positive/neutral/negative) Logistic Regression on TF-IDF.
- **Demand forecasting** — XGBoost on lag/rolling time-series features.
- **Web app** — Django with authentication + role-based authorization
  (customer / staff / admin), product catalog, cart, checkout, reviews.
- **UI** — elegant nude palette, English / नेपाली language toggle, NRS (Nepali Rupees) currency.

## Architecture
```
Browser ──▶ Django (:8001) ──requests──▶ FastAPI (:8000) ──▶ 3 .pkl models
              │  SQLite (db.sqlite3)
```

## Project layout
```
ecommerce-ml/
├── data/raw/          # the 3 real datasets (recommendation / sentiment / demand)
├── notebooks/         # ⭐ 3 separate Colab-ready notebooks (one per ML feature)
├── ml_training/       # train_recommendation / train_sentiment / train_sentiment_smote / train_demand
├── fastapi_ml/        # main.py (ML service) + models/*.pkl
├── django_app/        # Django project + apps: core, products, cart, orders, reviews, accounts
│   ├── templates/     # HTML (base + per-app)
│   ├── static/css/    # style.css (nude palette)
│   ├── seed.py        # populate catalog (links to recommendation item ids)
│   ├── remap_products.py  # re-theme catalog from the model's co-view clusters
│   └── seed_users.py  # create demo accounts
└── VIVA_CHEAT_SHEET.md
```

## Why the recommendations look sensible
The recommender is trained on the public **Retailrocket** event log (2.76M events /
1.4M visitors). Two layers sit on top of it — neither touches the trained model:

1. **Catalog re-theming** — `remap_products.py` clusters the 545 items using the
   model's **own** co-view similarity and gives each cluster one theme (shared name
   vocabulary + category).
2. **Evidence re-rank** — the product page asks for a deeper candidate pool (`k=20`)
   than it shows (4), then re-ranks on
   `0.5 × co-viewers + 0.4 × cosine + 0.25 × same-category`, because cosine is noisy
   on products with tiny audiences.

Result: **100%** of recommendations on 40 live pages share the clicked product's
category. See *§3A-bis* of the cheat sheet for the full honest answer.

```bash
python remap_products.py      # (from django_app/, with the project venv)
```

## Training notebooks (Colab-ready)
`notebooks/` holds three **separate** notebooks — each self-contained (install → load CSV →
train → evaluate with plots → save `.pkl`). Upload to Google Colab and *Run all*.

| Notebook | Feature | Algorithm |
|---|---|---|
| `01_recommendation.ipynb` | "You may also like" | item-item cosine CF (vs KNN) |
| `02_sentiment.ipynb` | Review sentiment | TF-IDF + Logistic Regression (vs NB, SVM) |
| `03_demand_forecast.ipynb` | Demand forecast | XGBoost time series (vs Random Forest) |

See `notebooks/README.md` for Colab steps and the dataset-date explanation.

## Setup
```bash
# 1. (one-time) create & activate the venv, then install deps
python -m venv venv
venv/Scripts/python -m pip install -r fastapi_ml/requirements.txt
venv/Scripts/python -m pip install django requests

# 2. Train the 3 models (already done — re-run if you change data)
cd ml_training && python train_recommendation.py
python train_sentiment.py
python train_demand.py        # saves winners into fastapi_ml/models/

# 3. Prepare the web database
cd ../django_app
python manage.py migrate
python seed.py                # 545 products
python seed_users.py          # demo accounts (password: DemoPass1234)

# 4. Seed realistic LOCAL data so all 3 ML features have something to work on
python manage.py seed_data            # ~20 customers, 260 orders (dated), 130 reviews, carts
python manage.py seed_data --reset    # wipe + reseed orders/reviews/carts
```

`DJANGO_SECRET_KEY` can be set in the environment for deployments. If it is not
set, Django uses a development-only fallback; do not use that fallback in production.

## Run
```bash
# terminal 1 — ML service
cd fastapi_ml && venv/Scripts/python -m uvicorn main:app --port 8000

# terminal 2 — web app
cd django_app && venv/Scripts/python manage.py runserver 127.0.0.1:8001
```
Open http://127.0.0.1:8001

## Demo accounts (password `DemoPass1234`)
| user | role | can |
|------|------|-----|
| `admin1` | admin | everything + Django admin |
| `staff1` | staff | shop, review, **open Demand Forecast dashboard** |
| `customer1` | customer | shop, cart, checkout, review |

> Note: the seeded demo hashes may differ on an existing DB; re-run `seed_users.py` (or reset the
> password) if a login fails. Superusers are `admin1` and `nancy123`.

## ML results (from the actual runs)
| Feature | Winner | Metric |
|---------|--------|--------|
| Recommendation | Cosine similarity | Precision@5 = 0.139 |
| Sentiment | Logistic Regression (class-weighted) | Macro-F1 = 0.633, Acc = 0.80 |
| Demand | XGBoost | RMSE = 7.68, MAE = 5.93 |

## Website data (so you can TEST the ML)
`python manage.py seed_data` fills the site with realistic **local** data:
- **20 customers** (login: any seeded username / `DemoPass1234`)
- **260 orders** backdated over ~8 months + 664 line items → gives a real **sales history**
- **130 reviews** with mixed text, each labelled by the **live `/sentiment` model**
  (spread: ~61 positive / 18 neutral / 51 negative)
- a few carts

Each product also carries `demand_sku` (1-50) linking it to the demand dataset, so the
admin dashboard can forecast for a real product AND show the store's own sales charts.

| Feature | Where to test it | What you should see |
|---|---|---|
| Recommendation | any product page | "You may also like" (4 cards) |
| Sentiment | submit a review (e.g. "very disappointed, bad quality") | coloured badge; appears in admin negative queue |
| Demand | `/accounts/dashboard/` (staff) | forecast chart + **sales history** charts + health metrics |

See `VIVA_CHEAT_SHEET.md` for the full explanation, code map, and likely questions.
