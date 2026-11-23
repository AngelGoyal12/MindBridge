
import pandas as pd
import joblib

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parents[1]

TRAIN_FILE = BASE_DIR / "data" / "processed" / "train.csv"
TEST_FILE = BASE_DIR / "data" / "processed" / "test.csv"

MODEL_DIR = BASE_DIR / "models"

RANDOM_SEED = 42

# 1. Load datasets
train_df = pd.read_csv(TRAIN_FILE)
test_df = pd.read_csv(TEST_FILE)

required_columns = {"title", "description", "category"}

if not required_columns.issubset(train_df.columns):
    raise ValueError("Training dataset is missing required columns.")

if not required_columns.issubset(test_df.columns):
    raise ValueError("Testing dataset is missing required columns.")

if train_df[list(required_columns)].isnull().any().any():
    raise ValueError("Missing values found in training dataset.")

if test_df[list(required_columns)].isnull().any().any():
    raise ValueError("Missing values found in testing dataset.")

if set(train_df["title"]).intersection(set(test_df["title"])):
    raise ValueError("Title leakage detected between train and test.")

# 2. Prepare input text and target labels
X_train = (
    train_df["title"].astype(str) + " " +
    train_df["description"].astype(str)
)

X_test = (
    test_df["title"].astype(str) + " " +
    test_df["description"].astype(str)
)

y_train = train_df["category"]
y_test = test_df["category"]

# 3. Convert text into numerical features
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

# 4. Train Logistic Regression
model = LogisticRegression(
    max_iter=2000,
    random_state=RANDOM_SEED
)

model.fit(X_train_tfidf, y_train)

# 5. Predict test categories
y_pred = model.predict(X_test_tfidf)

# 6. Evaluate model
labels = sorted(y_train.unique())

accuracy = accuracy_score(y_test, y_pred)

print("\n========== BASELINE MODEL RESULTS ==========")

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Accuracy percentage: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        labels=labels,
        zero_division=0
    )
)

print("\nConfusion Matrix:")
print("Category order:", labels)
print(confusion_matrix(y_test, y_pred, labels=labels))

# 7. Save model and vectorizer
MODEL_DIR.mkdir(parents=True, exist_ok=True)

joblib.dump(model, MODEL_DIR / "logistic_regression_model.joblib")
joblib.dump(vectorizer, MODEL_DIR / "tfidf_vectorizer.joblib")

print("\nSaved model:")
print(MODEL_DIR / "logistic_regression_model.joblib")

print("\nSaved vectorizer:")
print(MODEL_DIR / "tfidf_vectorizer.joblib")

print("\nBaseline training and evaluation completed.")
