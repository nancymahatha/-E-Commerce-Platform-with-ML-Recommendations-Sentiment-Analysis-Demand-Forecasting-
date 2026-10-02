"""
================================================================================
PHASE 3 - REVIEW SENTIMENT ANALYSIS  (FINAL: class-weight balanced)
================================================================================
Goal: label a review Positive / Neutral / Negative.

We compare THREE balanced candidates and keep the winner:
  - Logistic Regression   (class_weight via sample_weight = 'balanced')
  - Naive Bayes          (class_weight via sample_weight)
  - Linear SVM           (class_weight via sample_weight)

Imbalance fix = CLASS WEIGHTING (not SMOTE). We tried SMOTE too
(see train_sentiment_smote.py) but class-weighting scored higher Macro-F1
(0.633 vs 0.617) and keeps the full TF-IDF signal. Both are documented.

We keep the model_type/vectorizer/classifier bundle format so FastAPI can call
vectorizer.transform(text) -> classifier.predict(...).
================================================================================
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.utils.class_weight import compute_class_weight

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
# 5. TF-IDF + balanced sample weights
# ----------------------------------------------------------------------------- #
print("[4/7] TF-IDF vectorizing + balanced sample weights ...")
tfidf = TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                        min_df=5, stop_words="english")
Xtr = tfidf.fit_transform(X_train)
Xte = tfidf.transform(X_test)

cw = compute_class_weight("balanced", classes=np.arange(len(LABEL_NAMES)), y=y_train)
sw = np.array([cw[y] for y in y_train])

# ----------------------------------------------------------------------------- #
# 6. TRAIN + EVALUATE 3 BALANCED CANDIDATES
# ----------------------------------------------------------------------------- #
print("[5/7] Training 3 balanced candidates ...")
candidates = {
    "Logistic Regression": LogisticRegression(max_iter=1000, C=1.0),
    "Naive Bayes":         MultinomialNB(),
    "Linear SVM":          LinearSVC(),
}
results = {}
for name, clf in candidates.items():
    clf.fit(Xtr, y_train, sample_weight=sw)
    pred = clf.predict(Xte)
    results[name] = (accuracy_score(y_test, pred), f1_score(y_test, pred, average="macro"))

print(f"\n      {'Model':<22}{'Accuracy':>12}{'Macro-F1':>12}")
for name, (a, f) in results.items():
    print(f"      {name:<22}{a:>12.4f}{f:>12.4f}")

best_name = max(results, key=lambda n: (results[n][1], results[n][0]))
best_clf  = candidates[best_name]
w_acc, w_f1 = results[best_name]
print(f"\n[6/7] WINNER: {best_name}  (Accuracy={w_acc:.4f}, Macro-F1={w_f1:.4f})")

print("\n      Classification report (winner):")
print(classification_report(y_test, best_clf.predict(Xte),
                            target_names=LABEL_NAMES, digits=4))

# ----------------------------------------------------------------------------- #
# 7. SAVE WINNER  (vectorizer + classifier bundle for FastAPI)
# ----------------------------------------------------------------------------- #
type_map = {"Logistic Regression": "logistic_regression",
            "Naive Bayes": "naive_bayes",
            "Linear SVM": "linear_svm"}
bundle = {
    "model_type": type_map[best_name],
    "vectorizer": tfidf,
    "classifier": best_clf,
    "label_names": LABEL_NAMES,
    "metrics": {"accuracy": w_acc, "macro_f1": w_f1},
}
with open(os.path.join(MODEL_DIR, "sentiment_model.pkl"), "wb") as f:
    pickle.dump(bundle, f)
print(f"      saved -> {MODEL_DIR}/sentiment_model.pkl")

df[["text", "label", "y"]].to_csv(os.path.join(PROCESSED_DIR, "reviews_clean.csv"), index=False)

demo_texts = [
    "Absolutely wonderful - silky and sexy and comfortable, loved it!",
    "The material is cheap and ripped after one wash, very disappointed.",
    "It is okay, nothing special, fits fine but the color is a bit off.",
]
preds = best_clf.predict(tfidf.transform(demo_texts))
print("\n      Demo predictions:")
for t, p in zip(demo_texts, preds):
    print(f"        [{LABEL_NAMES[p]:>8}]  {t[:60]}...")

print("\nDONE Phase 3 (class-weight balanced).")
