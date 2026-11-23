
import pandas as pd
import re
from pathlib import Path
from collections import Counter
from itertools import combinations
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parents[1]

DATASET_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2.csv"
REPORT_DIR = BASE_DIR / "data" / "reports"

EXPECTED_CATEGORIES = {
    "academic_support",
    "hostel_issue",
    "ragging_bullying",
    "emotional_support",
    "financial_assistance",
    "other"
}

EXPECTED_COLUMNS = {
    "title",
    "description",
    "category",
    "data_source"
}

REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("\n========== MINDBRIDGE DATASET VALIDATION ==========\n")

if not DATASET_PATH.exists():
    print("ERROR: Dataset CSV not found.")
    print("Expected location:", DATASET_PATH)
    raise SystemExit

df = pd.read_csv(DATASET_PATH)

# 1. Basic information
print("1. BASIC INFORMATION")
print("Total records:", len(df))
print("Columns:", list(df.columns))

missing_columns = EXPECTED_COLUMNS - set(df.columns)

if missing_columns:
    print("Missing columns:", missing_columns)
    raise SystemExit

# 2. Missing values
print("\n2. MISSING VALUE CHECK")

for column in EXPECTED_COLUMNS:
    print(column, ":", df[column].isna().sum())

# 3. Blank values
print("\n3. BLANK VALUE CHECK")

for column in EXPECTED_COLUMNS:
    blank_count = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )
    print(column, ":", blank_count)

# 4. Category distribution
print("\n4. CATEGORY DISTRIBUTION")

category_counts = df["category"].value_counts()

print(category_counts)

print("\nMissing categories:")
print(EXPECTED_CATEGORIES - set(df["category"].dropna().unique()))

print("\nUnexpected categories:")
print(set(df["category"].dropna().unique()) - EXPECTED_CATEGORIES)

# 5. Data source check
print("\n5. DATA SOURCE DISTRIBUTION")
print(df["data_source"].value_counts(dropna=False))

# 6. Exact duplicate checks
print("\n6. DUPLICATE CHECKS")

print(
    "Duplicate descriptions:",
    df["description"].duplicated().sum()
)

print(
    "Duplicate title-description pairs:",
    df.duplicated(subset=["title", "description"]).sum()
)

# 7. Text length
print("\n7. TEXT LENGTH CHECK")

df["description_length"] = (
    df["description"].fillna("").astype(str).str.split().str.len()
)

print(df["description_length"].describe())

print("Descriptions shorter than 5 words:",
      (df["description_length"] < 5).sum())

print("Descriptions longer than 150 words:",
      (df["description_length"] > 150).sum())

# 8. Repeated title distribution
print("\n8. TITLE DISTRIBUTION")

print(df.groupby("category")["title"].nunique())

# 9. Similarity check
print("\n9. NEAR-DUPLICATE CHECK")

descriptions = (
    df["description"]
    .fillna("")
    .astype(str)
    .tolist()
)

if len(descriptions) > 1 and any(text.strip() for text in descriptions):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(descriptions)

    similarity_matrix = cosine_similarity(matrix)

    near_duplicates = []

    for i in range(len(descriptions)):
        for j in range(i + 1, len(descriptions)):
            score = similarity_matrix[i, j]

            if score >= 0.85:
                near_duplicates.append({
                    "index_1": i,
                    "index_2": j,
                    "similarity": round(float(score), 3),
                    "description_1": descriptions[i],
                    "description_2": descriptions[j]
                })

    print("Near-duplicate pairs (similarity >= 0.85):",
          len(near_duplicates))

    near_df = pd.DataFrame(near_duplicates)
    near_df.to_csv(
        REPORT_DIR / "near_duplicates.csv",
        index=False
    )
else:
    print("Not enough non-empty descriptions for similarity check.")

# 10. Repeated phrase check
print("\n10. COMMON PHRASES")

all_text = " ".join(descriptions).lower()

phrases = [
    "i would appreciate",
    "please help me",
    "i need help",
    "could someone",
    "please guide me",
    "i am struggling",
    "i am finding it difficult"
]

for phrase in phrases:
    print(
        phrase,
        ":",
        all_text.count(phrase)
    )

# 11. Save full validation report
df.to_csv(
    REPORT_DIR / "dataset_validation_details.csv",
    index=False
)

print("\n12. VALIDATION COMPLETED")
print("Reports saved in:", REPORT_DIR)

print("\nNOTE:")
print("Passing these checks does not prove semantic quality.")
print("Manually review near-duplicates, category relevance and labels.")



print("\n========== CATEGORY SAMPLE REVIEW ==========")

for category in sorted(df["category"].unique()):

    print(f"\n\nCATEGORY: {category.upper()}")

    category_data = df[df["category"] == category]

    samples = category_data.sample(
        n=10,
        random_state=42
    )

    for index, record in samples.iterrows():

        print("\nTitle:", record["title"])
        print("Description:", record["description"])
        print("Category:", record["category"])
