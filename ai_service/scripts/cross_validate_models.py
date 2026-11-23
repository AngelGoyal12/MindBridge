
import pandas as pd

from pathlib import Path
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, f1_score

BASE_DIR = Path(__file__).resolve().parents[1]

TRAIN_FILE = BASE_DIR / "data" / "processed" / "train.csv"

df = pd.read_csv(TRAIN_FILE)

X = df["title"].astype(str) + " " + df["description"].astype(str)
y = df["category"]
groups = df["title"]

cv = StratifiedGroupKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

models = {
    "Logistic Regression": LogisticRegression(
        max_iter=2000,
        random_state=42
    ),
    "Multinomial Naive Bayes": MultinomialNB()
}

results = {}

for name, model in models.items():
    accuracies = []
    f1_scores = []

    print("\n================================")
    print(name)
    print("================================")

    for fold, (train_idx, val_idx) in enumerate(
        cv.split(X, y, groups), start=1
    ):
        X_train = X.iloc[train_idx]
        X_val = X.iloc[val_idx]

        y_train = y.iloc[train_idx]
        y_val = y.iloc[val_idx]

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True
        )

        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_val_tfidf = vectorizer.transform(X_val)

        model.fit(X_train_tfidf, y_train)

        predictions = model.predict(X_val_tfidf)

        accuracy = accuracy_score(y_val, predictions)
        f1 = f1_score(
            y_val,
            predictions,
            average="macro",
            zero_division=0
        )

        accuracies.append(accuracy)
        f1_scores.append(f1)

        print(
            f"Fold {fold}: "
            f"Accuracy = {accuracy * 100:.2f}%, "
            f"Macro F1 = {f1:.4f}"
        )

    results[name] = {
        "accuracy": accuracies,
        "f1": f1_scores
    }

    print("\nAverage Accuracy:", round(
        sum(accuracies) / len(accuracies) * 100, 2
    ), "%")

    print("Average Macro F1:", round(
        sum(f1_scores) / len(f1_scores), 4
    ))

print("\n========== FINAL COMPARISON ==========")

for name, scores in results.items():
    print(
        name,
        "| Accuracy:",
        round(sum(scores["accuracy"]) / 5 * 100, 2),
        "%",
        "| Macro F1:",
        round(sum(scores["f1"]) / 5, 4)
    )

print("\nCross-validation completed.")
