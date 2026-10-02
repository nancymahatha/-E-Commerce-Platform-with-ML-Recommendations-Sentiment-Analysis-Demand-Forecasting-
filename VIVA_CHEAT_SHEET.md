# Viva Cheat-Sheet — E-Commerce ML Platform

> How to TALK about this project in your viva. Read top-to-bottom; every number here
> is from the actual runs on your machine (so it is defensible).

---

## 1. What is the project? (the 30-second pitch)
A full-stack e-commerce site with **three ML features**, built "train 2 (or 3), keep the best":

| # | Feature | Algorithm chosen | Why it won |
|---|---------|------------------|------------|
| 1 | Product recommendation | **Item-based Cosine similarity** | Beat KNN on Precision@5 (0.139 vs 0.110) |
| 2 | Review sentiment | **Logistic Regression** (class-weighted) | Best Macro-F1 0.633 (vs 0.617 for SMOTE) |
| 3 | Demand forecasting | **XGBoost** | Lowest RMSE 7.68 (vs 7.78 Random Forest) |

Architecture: **Django** (web, auth, SQLite DB) ↔ **FastAPI** (serves the 3 pickle models over HTTP) ↔ **real datasets** (not generated).

---

## 2. Architecture (draw this on the board)

```
        Browser
           │  HTTP  (English / नेपाली, NRS currency, Nude + Dashain themes)
           ▼
   ┌──────────────────┐        requests         ┌──────────────────────────┐
   │   Django  :8001  │ ─────────────────────▶ │   FastAPI  :8000         │
   │  - auth (roles)  │                         │  loads 3 .pkl models     │
   │  - products/cart │ ◀───────────────────── │  /recommend /sentiment   │
   │  - orders/reviews│      JSON results       │  /demand  /health        │
   └──────────────────┘                         └──────────────────────────┘
           │                                                │
           ▼ SQLite (db.sqlite3)                     loads from
        users, products,                            data/raw/*.csv
        carts, orders, reviews
```

---

## 3. Dataset → Preprocessing → Model → Result (per feature)

### 3A. Recommendation  (dataset: Retailrocket `events.csv`)
- **Raw:** timestamp, visitorid, event(view/addtocart/transaction), itemid. ~millions of rows, 99.9% empty (sparse).
- **Preprocessing:**
  1. Keep only the 3 interaction events; drop missing ids.
  2. Weight events: view=1, addtocart=2, transaction=3 (a purchase matters more than a view).
  3. Trim sparsity: keep top **600 items** + top **1500 users**.
  4. Time-based hold-out: hide each user's **most recent** interaction as the test item (never "predict" what they already did).
  5. Build user–item matrix R; compute **item–item cosine similarity**.
- **Two models compared:** full cosine similarity vs KNN (only 20 nearest).
- **Winner:** Cosine — Precision@5 = **0.139**, Recall@5 = **0.139**.
- **File:** `ml_training/train_recommendation.py`; saved `fastapi_ml/models/recommendation_model.pkl`.

### 3A-bis. "Why do the recommendations look random sometimes?" — HONEST ANSWER
This is the single most likely thing an examiner will probe, so know it cold.

**The model is real; the product NAME is a demo label.**
1. The similarity matrix is computed from **2.76M real events / 1.4M real visitors**
   in the Retailrocket log. Items that share an audience are genuinely similar
   **in that dataset**.
2. Our store's 545 products are demo rows. `seed.py` invented their names/prices
   and bolted each one onto a real dataset item id via `ml_item_id`.
3. So the recommender correctly returns a **dataset neighbour** — but if the demo
   name is random, the neighbour *reads* as unrelated.

**What we did about it (in order):**
- **Option B — semantic remap (`django_app/remap_products.py`):** we cluster the
  545 items using the model's OWN co-view similarity (spectral clustering on a
  top-5 sparsified graph, 25 clusters), then give every item in a cluster ONE
  theme (shared name vocabulary + category + price band). Now items the model
  treats as neighbours also *read* as neighbours → recommendations look sensible.
- **Re-rank on evidence (`products/views.py`):** the page asks the model for a
  **deeper candidate pool (k=20)** than it shows (4), then re-ranks that pool on a
  blend of signals the model already produced:
  `0.5 × normalised co-viewers + 0.4 × normalised cosine + 0.25 (same category)`.
  **Why:** cosine is noisy when an item has a thin audience (some products were
  viewed by only 1–14 shoppers), so a weak neighbour can out-rank a strong one.
  Co-viewer count is the hard evidence behind the score, so it leads.
  This is a **re-rank of the model's own output — the trained matrix is never
  modified.**
- **Measured result:** **100%** of recommendations on 40 live rendered pages share
  the clicked product's category (was ~90% raw; 3-seed offline average improved
  87%→93%).
- **API note:** `POST /recommend` accepted `k ≤ 20`; raised the cap to **50** so a
  caller can request a deeper pool for client-side re-ranking.
- **Honesty (Option A):** the remap + re-rank only change the DISPLAY ORDER. The
  similarity matrix, the model, and the metrics are unchanged. Nothing is faked.

**The one-line defence:** *"The recommender is trained on 2.7M real events from a
public dataset. It returns genuine neighbours. Two things were fixed on top of it:
the demo catalog was re-themed from the model's own clusters so names read
coherently, and the page re-ranks the model's own candidate pool on co-viewer
evidence — because cosine is noisy on products with tiny audiences. The trained
model is untouched. Retraining on our own logs would replace the bootstrap
dataset — same algorithm, our data."*

- **Bootstrap caveat:** with only ~1 site user, the dataset IS the recommender's
  only knowledge (cold start). The **item-based** feature ("you may also like")
  is fully independent of our users; the **user-based** home-page personalisation
  falls back to "popular items" until real browsing history exists.

### 3B. Sentiment  (dataset: Women's Clothing Reviews)
- **Raw:** Review Text + Title + Rating (1–5).
- **Preprocessing:** drop empty text; merge Title+Text; label by rating: ≥4→positive, =3→neutral, <3→negative. 80/20 stratified split. TF-IDF (10k features, 1–2 grams).
- **Imbalance problem:** neutral class is rare → models ignore it.
  - Tried **SMOTE** (`train_sentiment_smote.py`): Macro-F1 = 0.617.
  - Chose **class-weighting** (sample_weight = `compute_class_weight('balanced')`): Macro-F1 = **0.633** (higher, and keeps full TF-IDF signal).
- **Three candidates compared:** Logistic Regression, Naive Bayes, Linear SVM — all balanced.
- **Winner:** **Logistic Regression** — Accuracy **0.8015**, Macro-F1 **0.6331**.
- **File:** `ml_training/train_sentiment.py`; saved `sentiment_model.pkl`.

#### 3B-bis. "Who sees the sentiment prediction — and why isn't it public?"
- **Answer:** it is **staff/admin-only by design**. The sentiment label is an *internal triage
  signal*, not a shopper-facing feature. Two reasons: (1) a shopper gains nothing from seeing a
  machine's guess about another shopper's tone; (2) the model is a bag-of-words classifier with a
  known domain mismatch (trained on clothing reviews, applied to skincare), so publishing it would
  expose a weak number for no user benefit. So we keep it behind the counter.
- **What shoppers see:** the review text, the star rating, and (if applicable) the
  **Verified purchase** badge. **No sentiment badge.**
- **What staff/admin see** on the product page (`product_detail.html`, inside `{% if is_staff_role %}`):
  a compact **"Staff insight"** strip — *ML sentiment at a glance* — showing counts of
  positive / neutral / negative, the average model confidence, and a one-line flag
  ("⚠ negative reviews need attention" or "✓ all clear"). Each review row also shows the label and
  its confidence next to the author. That is the whole point: staff *get the gist at once* without
  reading every review.
- **How it is enforced (two layers, defence-in-depth):**
  1. `products/views.py` computes `sentiment_summary` **only** when
     `request.user.profile.is_staff_role()` is true — shoppers' template context never even
     contains the numbers.
  2. The template also guards with `{% if is_staff_role %}` (exposed to every template by
     `core/context_processors.py`).
- **Verified:** anonymous & customer → 0 sentiment markers in the HTML; staff & admin → strip +
  per-review label + confidence all present.
- **Talking point:** "The forecast dashboard is the same story — `/dashboard/` is wrapped in a
  `staff_required` decorator. ML output in this system is decision *support for staff*, not
  consumer-facing content."

### 3C. Demand forecasting  (dataset: Store Item Demand `train.csv`)
- **Raw:** date, store(1–10), item(1–50), sales — 913,000 rows, 5 years.
- **Preprocessing (TIME-SERIES aware — NO random shuffle!):**
  1. Date → year, month, day, dayofweek, weekofyear, is_weekend.
  2. Lag features: sales at t-1, t-7, t-14 (autocorrelation).
  3. Rolling means: 7-day and 30-day.
  4. **Time-based split:** train on earlier months, validate on the **last 90 days** (random split would leak future→past → invalid).
- **Two models compared:** Random Forest vs **XGBoost** (200 trees).
- **Winner:** **XGBoost** — MAE **5.93**, RMSE **7.68**.
- **Key insight:** feature importance shows `lag7` (0.64) and `roll7` (0.23) dominate → strong **weekly seasonality** (great viva talking point).
- **Inference:** recursive one-day-at-a-time forecasting (each prediction feeds the next day's lag/roll).
- **File:** `ml_training/train_demand.py`; saved `demand_model.pkl`.
- **Notebook:** `notebooks/03_demand_forecast.ipynb` (Colab-ready, explains the 2018 window).

#### 3C-bis. "On what basis does the forecast say that?" — the honest, plain answer
The staff dashboard shows a **"How we came up with this number"** panel that spells this out
on screen. Under the hood the answer is:

1. **It starts from real, recent sales.** For the chosen product the engine loads the **last 30
   days** of actual unit sales (stored in `demand_model.pkl` under `history[(store,item)]`).
   Everything is anchored to those real numbers — not to a random or generic average.
2. **It uses the learned pattern, not just the average.** The XGBoost model was trained on
   913,000 rows with features: **year, month, day, day-of-week, week-of-year, is_weekend**,
   the encoded store/item, and **lags (t-1, t-7, t-14)** + **rolling means (7-day, 30-day)**.
   Feature importance showed `lag7` (0.64) and `roll7` (0.23) dominate → the model mainly
   relies on **last week's demand** and the **weekly rhythm** (weekends busier). That is *why*
   it can beat a flat average.
3. **It rolls forward one day at a time (recursive).** Each predicted day is appended to the
   window and becomes the `lag1/lag7/roll7` input for the next day, for the requested horizon
   (30 days). Then the daily values are summed → **predicted total units**.
4. **It is honest about error.** On the held-out last 90 days it scored **MAE ≈ 5.93 / RMSE ≈ 7.68**
   units per day — i.e. "typically off by about 6–8 units/day". The dashboard shows this as a
   close estimate, not a promise.

**One-line defence:** *"The forecast is a regression on the last 30 days of real sales, using the
day-of-week and lag structure the model learned from five years of history — that's why it can
produce a specific number and why it comes with a stated error of ~6–8 units/day."*

> Note: the demand model is trained on the Kaggle **Store Item Demand** dataset (SKUs 1–50), and
> each catalogue product carries a `demand_sku` (1–50) that maps it onto that model — the same
> bridging idea as `ml_item_id` for recommendations. Because ~545 catalogue products share only 50
> SKUs (~11 products per SKU), the dashboard dropdown lists **every product** and the view keeps the
> **exact product object the staff picked** (by primary key), then forecasts on *that* product's
> `demand_sku`. It never re-derives the product from the SKU, so the headline always names the picked
> product instead of some other product that happens to share the same SKU.

---

## 3D. "Why is the data from 2018 / old?" — the dates question
- **Demand `train.csv`:** 2013-01-01 → 2017-12-31 (913,000 rows, what we actually train on).
- **Demand `test.csv`:** **2018-01-01 → 2018-03-31** (45,000 rows) — this is the Kaggle
  competition's *target window*. **That is where "2018" comes from.** Our model does not output
  or hard-code 2018; it forecasts forward from the last training date.
- **Recommendation `events.csv`** (Retailrocket): events in **mid-2015**.
- **Sentiment reviews:** **no date column** at all (23,486 rows, rating-labelled).
- **Why older public data?**
  1. These are the **standard public benchmark datasets** for these exact tasks → my metrics are
     comparable to published numbers and an examiner can check them.
  2. A student project has **no live traffic**, so there is no "2026 dataset" to train on; recent
     real transaction data is proprietary and not public.
  3. The models are **retrainable**: drop a newer CSV into `data/raw/<task>/` and re-run
     `ml_training/train_*.py` or the notebook — no application code changes.
- **One-line answer:** *"The data is historical because public benchmark data is what's available
  and comparable; the system is live and retrains on any new CSV without code changes."*

---

## 4. Code map (where to point during the demo)
| You want to show… | File |
|---|---|
| Recommendation training | `ml_training/train_recommendation.py` |
| Sentiment training (final) | `ml_training/train_sentiment.py` |
| Sentiment w/ SMOTE (the "we tried" story) | `ml_training/train_sentiment_smote.py` |
| Demand training | `ml_training/train_demand.py` |
| Colab notebooks (all 3, separate) | `notebooks/01_recommendation.ipynb`, `02_sentiment.ipynb`, `03_demand_forecast.ipynb` |
| ML service endpoints | `fastapi_ml/main.py` |
| Django↔ML calls | `core/ml_client.py` |
| Auth + roles | `accounts/models.py`, `accounts/decorators.py` |
| Product + recs + reviews page | `products/views.py`, `templates/products/product_detail.html` |
| Staff demand dashboard (plain-language console) | `accounts/views.py` (`demand_dashboard`), `templates/accounts/demand_dashboard.html` |
| Admin back-office (full CRUD for staff) | `products/admin.py`, `orders/admin.py`, `reviews/admin.py`, `cart/admin.py`, `accounts/admin.py`, `core/admin.py` (branding) |
| Bilingual + theme | `core/translations.py`, `core/context_processors.py`, `static/css/style.css` |

> **Note for the demo:** the staff-facing dashboard is deliberately written in plain
> language (no "cosine similarity / TF-IDF / XGBoost / ports" on screen) so a
> non-technical shop owner can use it. The *technical* story lives here in this
> cheat sheet and in `fastapi_ml/main.py` / `ml_training/*` — that is the file to
> open if the examiner asks *how* the models work. All store CRUD (products,
> categories, orders, reviews, users/roles) is done in the Django admin at
> `/admin/`, with search, filters and inline editing.

---

## 5. How to run (live demo)
```bash
# terminal 1 — ML service
cd ecommerce-ml/fastapi_ml
<venv>/python -m uvicorn main:app --port 8000

# terminal 2 — web app
cd ecommerce-ml/django_app
<venv>/python manage.py runserver 127.0.0.1:8001
```
Demo accounts (password **pass1234**): `admin1` (admin), `staff1` (staff → sees demand dashboard), `customer1` (shop + review).

---

## 6. Likely viva questions + crisp answers
**Q: Why item-based and not user-based CF?**  
Item-based is more stable & scalable; similar items co-occur even for new users, and it doesn't need a full user vector at inference.

**Q: Why cosine similarity?**  
Items are sparse high-dimensional vectors; cosine ignores magnitude and captures *direction* of co-interaction — robust to popularity bias.

**Q: Why class-weighting over SMOTE for sentiment?**  
SMOTE synthesizes minority samples (risk of noise/overfitting) and needs a Pipeline (TF-IDF→SVD→SMOTE→clf). Class-weighting just re-weights the loss, keeps the real TF-IDF signal, and scored higher Macro-F1 (0.633 vs 0.617). We keep SMOTE as an alternative (`train_sentiment_smote.py`).

**Q: Why a time-based split for demand, not train/test random?**  
Demand is a time series. A random split leaks future sales into training → unrealistically good, invalid forecast. Last-90-days hold-out mirrors real deployment.

**Q: Why XGBoost over Random Forest?**  
Gradient boosting corrects residuals sequentially → lower RMSE here (7.68 vs 7.78). RF is faster to train and less prone to overfit, but XGBoost won on error.

**Q: How do the two services talk?**  
Django calls FastAPI over HTTP using `requests` (`core/ml_client.py`); each endpoint returns JSON. FastAPI loads pickles once at startup. If ML is down, the UI degrades gracefully (recommendations/predictions simply hidden).

**Q: How is authorization enforced?**  
Django `User` handles authentication; `UserProfile.role` (customer/staff/admin) + a `staff_required` decorator gate the demand dashboard. A signal auto-creates a profile on user creation.

**Q: Who can see the ML predictions — are they public?**  
No. Recommendations ("You may also like") are the only ML output shoppers see, because they *help* the shopper. Sentiment labels and the demand forecast are **staff/admin-only** — they are internal decision support. Sentiment is hidden two ways: the view only computes the rollup for staff/admin, and the template guards with `{% if is_staff_role %}`. Verified: anonymous and customer sessions receive zero sentiment markup.

**Q: What are the limitations?**  
Recommendation trained on an external dataset (Retailrocket) and bridged via `ml_item_id`; sentiment is 3-class on review text only; demand uses historical sales with recursive forecasting (error accumulates over long horizons).
