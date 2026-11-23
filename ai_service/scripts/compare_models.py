
import random
import pandas as pd

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report

BASE_DIR = Path(__file__).resolve().parents[1]

TRAIN_FILE = BASE_DIR / "data" / "processed" / "train.csv"

RANDOM_SEED = 42
VALIDATION_TITLES_PER_CATEGORY = 3

df = pd.read_csv(TRAIN_FILE)

rng = random.Random(RANDOM_SEED)

train_parts = []
validation_parts = []

for category in sorted(df["category"].unique()):
    category_df = df[df["category"] == category].copy()

    titles = sorted(category_df["title"].unique())

    if len(titles) != 12:
        raise ValueError(
            f"{category} has {len(titles)} titles instead of 12."
        )

    rng.shuffle(titles)

    validation_titles = set(
        titles[:VALIDATION_TITLES_PER_CATEGORY]
    )

    train_parts.append(
        category_df[~category_df["title"].isin(validation_titles)]
    )

    validation_parts.append(
        category_df[category_df["title"].isin(validation_titles)]
    )

train_df = pd.concat(train_parts, ignore_index=True)
validation_df = pd.concat(validation_parts, ignore_index=True)

train_titles = set(train_df["title"])
validation_titles = set(validation_df["title"])

if train_titles.intersection(validation_titles):
    raise ValueError("Title leakage detected.")

if len(train_df) != 1080 or len(validation_df) != 360:
    raise ValueError("Unexpected train/validation record counts.")

X_train = (
    train_df["title"].astype(str) + " " +
    train_df["description"].astype(str)
)

X_validation = (
    validation_df["title"].astype(str) + " " +
    validation_df["description"].astype(str)
)

y_train = train_df["category"]
y_validation = validation_df["category"]

vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_validation_tfidf = vectorizer.transform(X_validation)

models = {
    "Logistic Regression": LogisticRegression(
        max_iter=2000,
        random_state=RANDOM_SEED
    ),
    "Multinomial Naive Bayes": MultinomialNB()
}

for name, model in models.items():
    model.fit(X_train_tfidf, y_train)

    predictions = model.predict(X_validation_tfidf)

    print("\n================================")
    print(name)
    print("================================")

    print(
        "Accuracy:",
        round(accuracy_score(y_validation, predictions) * 100, 2),
        "%"
    )

    print(
        classification_report(
            y_validation,
            predictions,
            zero_division=0
        )
    )

print("\n========== SPLIT VERIFICATION ==========")

print("Original training file records:", len(df))
print("Training records:", len(train_df))
print("Validation records:", len(validation_df))

print("\nTraining category counts:")
print(train_df["category"].value_counts().sort_index())

print("\nValidation category counts:")
print(validation_df["category"].value_counts().sort_index())

print("\nTraining titles:", len(train_titles))
print("Validation titles:", len(validation_titles))
print("Overlapping titles:", len(train_titles.intersection(validation_titles)))

print("\nModel comparison completed.")
