# Notebooks (Colab-ready)

Three **separate** training notebooks, one per ML feature. Each is self-contained: open it in
Google Colab, run the cells top to bottom, and it trains, evaluates (with plots) and saves its
`.pkl` model. No repo files are required except the dataset CSV.

| Notebook | Feature | Algorithm | Dataset | Live metric |
|---|---|---|---|---|
| `01_recommendation.ipynb` | "You may also like" | item-item **cosine** CF (vs KNN) | Retailrocket `events.csv` | precision@5 **0.139** |
| `02_sentiment.ipynb` | Review sentiment | **TF-IDF + Logistic Regression** (vs NB, SVM) | Women's Clothing Reviews | acc **0.802** / macro-F1 **0.633** |
| `03_demand_forecast.ipynb` | Demand forecast | **XGBoost** time series (vs Random Forest) | Store Item Demand `train.csv` | RMSE **7.68** |

These notebooks reproduce the exact results the live FastAPI service reports at `/health`,
so the numbers in your viva match the numbers in the notebooks.

---

## How to run in Google Colab

1. Go to **https://colab.research.google.com** → **File ▸ Upload notebook** → pick one `.ipynb`.
2. Run the **install** cell first (it pip-installs `pandas numpy scikit-learn xgboost matplotlib`).
3. Run the **load** cell. It looks for the CSV in this order:
   - already in the Colab working dir, or
   - the repo path `data/raw/...` (if you uploaded the repo), or
   - otherwise it opens a **file picker** — upload the CSV.
4. **Run all** (`Runtime ▸ Run all`). Each notebook ends by saving its model to `/content/models/`
   and offering a **download** — drop that file into `fastapi_ml/models/` in the repo.

> Tip: enable the GPU/CPU runtime you prefer, but none of these need a GPU. CPU runtime is enough.

## Datasets

Download the three CSVs from Kaggle and keep them next to the notebook (or upload when prompted):

- **Retailrocket E-commerce Dataset** → `events.csv`
- **Women's Clothing E-Commerce Reviews** → `Womens Clothing E-Commerce Reviews.csv`
- **Store Item Demand Forecasting Challenge** → `train.csv`

## About the dates (the "2018" question)

- The demand dataset's **`train.csv` covers 2013-01-01 → 2017-12-31**.
- The competition's **`test.csv` covers 2018-01-01 → 2018-03-31** — that is where the year
  **2018** comes from. It is the original public dataset's target window, **not** a date our
  model generates or hard-codes.
- The sales data is historical because these are the standard **public benchmark** datasets for
  these tasks (there is no public, recent, real transaction data). The models are **retrainable**:
  drop a newer CSV into `data/raw/<task>/` and re-run the notebook — no code changes.

## Files here

- `01_recommendation.ipynb` — Phase 2
- `02_sentiment.ipynb` — Phase 3
- `03_demand_forecast.ipynb` — Phase 4

The equivalent command-line scripts remain in `../ml_training/train_*.py`.
