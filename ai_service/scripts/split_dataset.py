
import pandas as pd
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2_2.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

RANDOM_SEED = 42
TEST_RATIO = 0.20

df = pd.read_csv(INPUT_FILE)

required_columns = {"title", "description", "category"}
if not required_columns.issubset(df.columns):
    raise ValueError("Dataset is missing required columns.")

if df[list(required_columns)].isnull().any().any():
    raise ValueError("Missing values found. Fix the dataset before splitting.")

train_parts = []
test_parts = []

rng = random.Random(RANDOM_SEED)

for category in sorted(df["category"].unique()):
    category_df = df[df["category"] == category].copy()

    titles = sorted(category_df["title"].unique())

    if len(titles) != 15:
        raise ValueError(
            f"{category} has {len(titles)} titles instead of 15."
        )

    rng.shuffle(titles)

    test_title_count = round(len(titles) * TEST_RATIO)
    test_titles = set(titles[:test_title_count])
    train_titles = set(titles[test_title_count:])

    train_category = category_df[
        category_df["title"].isin(train_titles)
    ]

    test_category = category_df[
        category_df["title"].isin(test_titles)
    ]

    train_parts.append(train_category)
    test_parts.append(test_category)

train_df = pd.concat(train_parts, ignore_index=True)
test_df = pd.concat(test_parts, ignore_index=True)

train_df = train_df.sample(frac=1, random_state=RANDOM_SEED)
test_df = test_df.sample(frac=1, random_state=RANDOM_SEED)

train_df = train_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)

train_titles = set(train_df["title"])
test_titles = set(test_df["title"])

if train_titles.intersection(test_titles):
    raise ValueError("Data leakage detected: titles overlap.")

if len(train_df) + len(test_df) != len(df):
    raise ValueError("Some records are missing from the split.")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

train_df.to_csv(OUTPUT_DIR / "train.csv", index=False)
test_df.to_csv(OUTPUT_DIR / "test.csv", index=False)

print("\n========== DATASET SPLIT SUMMARY ==========")

print("Original records:", len(df))
print("Training records:", len(train_df))
print("Testing records:", len(test_df))

print("\nTraining category distribution:")
print(train_df["category"].value_counts().sort_index())

print("\nTesting category distribution:")
print(test_df["category"].value_counts().sort_index())

print("\nOverlapping titles:", len(train_titles.intersection(test_titles)))

print("\nSaved files:")
print(OUTPUT_DIR / "train.csv")
print(OUTPUT_DIR / "test.csv")

print("\nDataset split completed successfully.")
