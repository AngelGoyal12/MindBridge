
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2_1.csv"
OUTPUT_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2_2.csv"

KEEP_CATEGORIES = [
    "academic_support",
    "hostel_issue",
    "ragging_bullying"
]

WEAK_CATEGORIES = [
    "emotional_support",
    "financial_assistance",
    "other"
]

GENERIC_ENDINGS = {
    "emotional_support": [
        "I would appreciate guidance on the support available for this situation.",
        "I would like to discuss this concern with the student counselling team.",
        "Please let me know how I can access appropriate emotional support.",
        "I would prefer to speak with someone who can help me manage this situation."
    ],
    "financial_assistance": [
        "I would appreciate guidance about the available financial assistance process.",
        "Please let me know which documents are required for this request.",
        "I would like to understand the next steps and eligibility conditions.",
        "Could the concerned department review my situation and guide me?"
    ],
    "other": [
        "I would appreciate guidance from the department responsible for this service.",
        "Please let me know the correct procedure for resolving this issue.",
        "Could someone direct me to the appropriate college office?",
        "I would like to know the next steps for getting this matter resolved."
    ]
}

INTENTS = {
    "Homesickness support": "adjusting to living away from home and managing homesickness",
    "Anxiety support request": "accessing counselling support for anxiety",
    "Loneliness and isolation": "finding support for loneliness and social isolation",
    "Personal stress support": "discussing personal stress in a confidential setting",
    "Motivation difficulties": "understanding and addressing emotional exhaustion",
    "Relationship stress support": "working through the emotional impact of a personal relationship concern",
    "Confidence improvement support": "building confidence in everyday interactions",
    "Emotional distress support": "speaking with a trained person about emotional distress",
    "Adjustment difficulties": "adjusting emotionally to college life",
    "Burnout support request": "managing emotional exhaustion and restoring a manageable routine",
    "Difficulty managing emotions": "developing healthier ways to manage strong emotions",
    "Social interaction difficulties": "becoming more comfortable in social situations",
    "Confidential emotional support": "arranging a private and confidential counselling discussion",
    "Academic pressure related stress": "managing emotional stress caused by college responsibilities",
    "Personal well-being support": "understanding changes in emotional well-being",

    "Scholarship application support": "completing a scholarship application",
    "Fee payment difficulty": "discussing options when semester fees cannot be paid on time",
    "Financial aid request": "applying for financial assistance to continue education",
    "Scholarship eligibility query": "checking scholarship eligibility requirements",
    "Education loan guidance": "understanding education loan options and the application process",
    "Fee deadline extension": "requesting additional time to pay semester fees",
    "Financial documentation support": "preparing documents for a financial assistance application",
    "Scholarship renewal issue": "resolving an issue with scholarship renewal",
    "Hostel fee assistance": "finding financial support for hostel fee payment",
    "Financial aid application status": "checking the progress of a submitted financial aid application",
    "Fee concession request": "understanding and applying for a fee concession",
    "Emergency financial assistance": "requesting urgent financial support for an unexpected situation",
    "Scholarship payment delay": "checking the delay in an approved scholarship payment",
    "Financial support eligibility": "identifying financial support schemes for which I may qualify",
    "Installment payment request": "requesting permission to pay college fees in installments",

    "Student identity card issue": "getting a student identity card issue resolved",
    "College event registration": "completing registration for a college event",
    "Administrative process query": "following the correct administrative procedure",
    "Document verification support": "completing verification of college documents",
    "Transport facility query": "getting information about the college transport service",
    "Library service complaint": "resolving an issue with the college library service",
    "Certificate request": "applying for and collecting an official college certificate",
    "Timetable information request": "confirming the updated class timetable",
    "College portal issue": "reporting and resolving an issue on the college portal",
    "Event participation query": "understanding requirements for participating in a college event",
    "Administrative office guidance": "identifying the correct administrative office",
    "Document submission query": "submitting college documents correctly",
    "Campus facility information": "finding information about a campus facility and its usage",
    "Student service request": "accessing a student service provided by the college",
    "General college enquiry": "finding the appropriate department for a college-related question"
}

ENDING_TEMPLATES = {
    "emotional_support": [
        "Could the counselling team help me with {intent}?",
        "I would like to understand how to get support for {intent}.",
        "Please guide me on the next step for {intent}.",
        "A private discussion would help me work on {intent}."
    ],
    "financial_assistance": [
        "Could the finance office guide me through {intent}?",
        "Please explain the next step for {intent}.",
        "I would appreciate help from the relevant office with {intent}.",
        "Could the concerned team review my request about {intent}?"
    ],
    "other": [
        "Could the relevant office help me with {intent}?",
        "Please guide me to the correct process for {intent}.",
        "I would appreciate assistance from the responsible team with {intent}.",
        "Could you clarify the next step for {intent}?"
    ]
}


def rebuild_description(row, category):
    title = row["title"]
    description = str(row["description"]).strip()

    if title not in INTENTS:
        raise ValueError(f"Missing intent mapping: {title}")

    matched_index = None
    core_description = None

    for index, ending in enumerate(GENERIC_ENDINGS[category]):
        suffix = " " + ending

        if description.endswith(suffix):
            core_description = description[:-len(suffix)].strip()
            matched_index = index
            break

    if matched_index is None:
        raise ValueError(
            f"Could not identify old ending for: {title}"
        )

    new_ending = ENDING_TEMPLATES[category][matched_index].format(
        intent=INTENTS[title]
    )

    return f"{core_description} {new_ending}"


def main():

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"V2.1 dataset not found: {INPUT_PATH}"
        )

    df = pd.read_csv(INPUT_PATH)

    required_columns = {
        "title",
        "description",
        "category",
        "data_source"
    }

    if not required_columns.issubset(df.columns):
        raise ValueError("Required columns are missing.")

    if len(df) != 1800:
        raise ValueError("V2.1 must contain exactly 1800 records.")

    parts = []

    # Preserve approved categories without modifying descriptions.
    preserved = df[
        df["category"].isin(KEEP_CATEGORIES)
    ].copy()

    for category in KEEP_CATEGORIES:
        count = (preserved["category"] == category).sum()

        if count != 300:
            raise ValueError(
                f"{category}: expected 300, found {count}"
            )

    parts.append(preserved)

    # Improve the remaining three categories.
    for category in WEAK_CATEGORIES:

        category_df = df[
            df["category"] == category
        ].copy()

        if len(category_df) != 300:
            raise ValueError(
                f"{category}: expected 300 source records"
            )

        category_df["description"] = category_df.apply(
            lambda row: rebuild_description(row, category),
            axis=1
        )

        parts.append(category_df)

        print(category, ":", len(category_df), "records improved")

    final_df = pd.concat(parts, ignore_index=True)

    final_df = final_df.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    # Final validation.
    if len(final_df) != 1800:
        raise ValueError("Expected 1800 records.")

    if final_df.isnull().any().any():
        raise ValueError("Missing values detected.")

    if final_df["description"].str.strip().eq("").any():
        raise ValueError("Blank descriptions detected.")

    if final_df["description"].duplicated().any():
        raise ValueError("Duplicate descriptions detected.")

    if final_df["title"].isnull().any():
        raise ValueError("Missing titles detected.")

    for category in KEEP_CATEGORIES + WEAK_CATEGORIES:

        count = (final_df["category"] == category).sum()

        if count != 300:
            raise ValueError(
                f"{category}: expected 300, found {count}"
            )

    # Confirm preserved categories are unchanged.
    for category in KEEP_CATEGORIES:

        old = df[df["category"] == category].sort_values(
            ["title", "description"]
        ).reset_index(drop=True)

        new = final_df[
            final_df["category"] == category
        ].sort_values(
            ["title", "description"]
        ).reset_index(drop=True)

        if not old[
            ["title", "description", "category", "data_source"]
        ].equals(
            new[
                ["title", "description", "category", "data_source"]
            ]
        ):
            raise ValueError(
                f"Preserved category changed: {category}"
            )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    final_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8"
    )

    print("\n========== V2.2 SUMMARY ==========")
    print("Total records:", len(final_df))
    print("\nCategory distribution:")
    print(final_df["category"].value_counts().sort_index())
    print("\nUnique descriptions:", final_df["description"].nunique())
    print("Unique titles:", final_df["title"].nunique())
    print("\nSaved successfully:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
