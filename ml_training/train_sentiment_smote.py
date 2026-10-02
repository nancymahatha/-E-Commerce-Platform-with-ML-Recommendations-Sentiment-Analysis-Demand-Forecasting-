"""
================================================================================
PHASE 3 - REVIEW SENTIMENT ANALYSIS  (Lesson 3, improved with SMOTE)
================================================================================
Goal: label a review Positive / Neutral / Negative.

Compare THREE strong candidates and keep the winner:
  - Logistic Regression
  - Linear SVM
  - Random Forest   (non-linear, robust "good" model)

Imbalance fix = SMOTE (synthetic minority oversampling) instead of class_weight.
SMOTE is placed INSIDE an imblearn Pipeline, so it resamples ONLY the training
data during fit and is skipped at prediction time -> no test leakage.

Pipeline per model:
  TF-IDF  ->  TruncatedSVD(300)  ->  SMOTE  ->  classifier
  (text)     (compress to 300d)     (balance)   (predict)

Why TruncatedSVD before SMOTE? SMOTE needs dense vectors; 10k TF-IDF dims would
be huge. SVD compresses to 300 dense dims -> SMOTE is fast and memory-safe. This
also often improves generalization.
================================================================================
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

RAW_CSV      = "data/raw/sentiment/Womens Clothing E-Commerce Reviews.csv"
PROCESSED_DIR = "data/processed/sentiment"
MODEL_DIR    = "fastapi_ml/models"
RANDOM_STATE = 42

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ----------------------------------------------------------------------------- #
# 1. LOAD + DROP EMPTY TEXT
# ----------------------------------------------------------------------------- #
print("[1/7] Loading reviews CSV ...")
df = pd.read_csv(RAW_CSV)
print(f"      raw rows: {len(df):,}")
before = len(df)
df = df.dropna(subset=["Review Text"])
df = df[df["Review Text"].str.strip() != ""]
print(f"      dropped {before - len(df):,} empty -> {len(df):,} usable")

# ----------------------------------------------------------------------------- #
# 2. MERGE TITLE + TEXT
# ----------------------------------------------------------------------------- #
df["text"] = (df["Title"].fillna("") + " " + df["Review Text"].fillna("")).str.strip()

# ----------------------------------------------------------------------------- #
# 3. LABEL BY RATING
# ----------------------------------------------------------------------------- #
def label(r):
    if r >= 4: return "positive"
    if r == 3: return "neutral"
    return "negative"
df["label"] = df["Rating"].apply(label)
LABEL_NAMES = ["negative", "neutral", "positive"]
df["y"] = df["label"].map({n: i for i, n in enumerate(LABEL_NAMES)})
print("[2/7] class counts:")
print(df["label"].value_counts().to_string())

# ----------------------------------------------------------------------------- #
# 4. STRATIFIED SPLIT
# ----------------------------------------------------------------------------- #
print("[3/7] Stratified 80/20 split ...")
X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["y"], test_size=0.2, random_state=RANDOM_STATE, stratify=df["y"])

# ----------------------------------------------------------------------------- #
# 5. BUILD + TRAIN + EVALUATE 3 CANDIDATES (each with SMOTE in its pipeline)
# ----------------------------------------------------------------------------- #
print("[4/7] Training 3 candidates with SMOTE (inside pipeline) ...")

def make_pipeline(clf):
    return ImbPipeline([
        ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                                   min_df=5, stop_words="english")),
        ("svd",   TruncatedSVD(n_components=300, random_state=RANDOM_STATE)),
        ("smote", SMOTE(random_state=RANDOM_STATE)),
        ("clf",   clf),
    ])

candidates = {
    "Logistic Regression": LogisticRegression(max_iter=1000, C=1.0),
    "Linear SVM":          LinearSVC(),
    "Random Forest":       RandomForestClassifier(n_estimators=200, n_jobs=-1,
                                                 random_state=RANDOM_STATE),
}
results, pipes = {}, {}
for name, clf in candidates.items():
    pipe = make_pipeline(clf)
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    results[name] = (accuracy_score(y_test, pred), f1_score(y_test, pred, average="macro"))
    pipes[name] = pipe
    print(f"      {name:<22} done")

print(f"\n      {'Model':<22}{'Accuracy':>12}{'Macro-F1':>12}")
for name, (a, f) in results.items():
    print(f"      {name:<22}{a:>12.4f}{f:>12.4f}")

# ----------------------------------------------------------------------------- #
# 6. PICK WINNER (higher Macro-F1; tie-break Accuracy)
# ----------------------------------------------------------------------------- #
best_name = max(results, key=lambda n: (results[n][1], results[n][0]))
best_pipe = pipes[best_name]
w_acc, w_f1 = results[best_name]
print(f"\n[5/7] WINNER: {best_name}  (Accuracy={w_acc:.4f}, Macro-F1={w_f1:.4f})")

print("\n      Classification report (winner):")
print(classification_report(y_test, best_pipe.predict(X_test),
                            target_names=LABEL_NAMES, digits=4))

# ----------------------------------------------------------------------------- #
# 7. SAVE WINNER
# ----------------------------------------------------------------------------- #
type_map = {"Logistic Regression": "logistic_regression",
            "Linear SVM": "linear_svm",
            "Random Forest": "random_forest"}
bundle = {
    "model_type": type_map[best_name],
    "pipeline": best_pipe,          # one object: tfidf -> svd -> smote -> clf
    "label_names": LABEL_NAMES,
    "metrics": {"accuracy": w_acc, "macro_f1": w_f1},
}
with open(os.path.join(MODEL_DIR, "sentiment_model.pkl"), "wb") as f:
    pickle.dump(bundle, f)
print(f"[6/7] saved -> {MODEL_DIR}/sentiment_model.pkl")

df[["text", "label", "y"]].to_csv(os.path.join(PROCESSED_DIR, "reviews_clean.csv"), index=False)

# ----------------------------------------------------------------------------- #
# DEMO
# ----------------------------------------------------------------------------- #
demo_texts = [
    "Absolutely wonderful - silky and sexy and comfortable, loved it!",
    "The material is cheap and ripped after one wash, very disappointed.",
    "It is okay, nothing special, fits fine but the color is a bit off.",
]
preds = best_pipe.predict(demo_texts)
print("\n[7/7] Demo predictions:")
for t, p in zip(demo_texts, preds):
    print(f"        [{LABEL_NAMES[p]:>8}]  {t[:60]}...")

print("\nDONE Phase 3 (SMOTE).")
