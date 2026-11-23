
import pandas as pd
import random
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[1]

V2_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2.csv"
OUTPUT_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2_1.csv"

RECORDS_PER_CATEGORY = 300

# Keep the three previously reviewed categories unchanged.
KEEP_CATEGORIES = [
    "academic_support",
    "hostel_issue",
    "ragging_bullying"
]

# Improved scenarios for the three weak categories.
# Each scenario has 20 relevant variations.
IMPROVED_SCENARIOS = {

    "emotional_support": [
        (
            "Homesickness support",
            "I have been missing my family and struggling to adjust to living away from home.",
            [
                "I often feel lonely in the evenings.",
                "This has been affecting my emotional well-being.",
                "I find it difficult to feel settled in the hostel.",
                "I would like to speak with someone who understands this situation.",
                "I miss the support I used to receive at home."
            ]
        ),
        (
            "Anxiety support request",
            "I have been experiencing anxiety that is affecting my everyday life.",
            [
                "I sometimes feel overwhelmed even during ordinary activities.",
                "I would like guidance from a trained counsellor.",
                "These feelings have been difficult to manage alone.",
                "I want to understand what counselling support is available.",
                "I would prefer to discuss this in a private setting."
            ]
        ),
        (
            "Loneliness and isolation",
            "I have been feeling lonely and disconnected from people around me.",
            [
                "I find it difficult to build close friendships.",
                "I often feel left out during social activities.",
                "I would like support in dealing with these feelings.",
                "This has started affecting my daily routine.",
                "I want to talk to someone without feeling judged."
            ]
        ),
        (
            "Personal stress support",
            "Personal circumstances have been causing me considerable emotional stress.",
            [
                "I have difficulty discussing these concerns with people I know.",
                "I would appreciate a confidential conversation.",
                "The situation has been affecting my peace of mind.",
                "I would like help understanding how to manage this stress.",
                "I think speaking with a counsellor may help."
            ]
        ),
        (
            "Motivation difficulties",
            "I have been feeling emotionally drained and finding it difficult to stay motivated.",
            [
                "Even simple daily activities have started feeling exhausting.",
                "I would like help understanding why I feel this way.",
                "I have not been feeling like myself recently.",
                "I would appreciate emotional support.",
                "I want to discuss ways to improve my well-being."
            ]
        ),
        (
            "Relationship stress support",
            "A personal relationship problem has been affecting my emotional well-being.",
            [
                "I have been finding it difficult to deal with the situation.",
                "I would like to discuss my feelings with someone impartial.",
                "The matter has been causing me ongoing stress.",
                "I would prefer a private counselling session.",
                "I need guidance on handling this situation."
            ]
        ),
        (
            "Confidence improvement support",
            "I have been struggling with low self-confidence in my everyday interactions.",
            [
                "I often doubt myself when communicating with others.",
                "I feel uncomfortable expressing my opinions.",
                "I would like support in building confidence.",
                "This concern has been affecting my social life.",
                "I want to discuss this with a support professional."
            ]
        ),
        (
            "Emotional distress support",
            "I have been feeling emotionally disturbed and need someone to talk to.",
            [
                "I have difficulty explaining what I am going through.",
                "I would appreciate a patient and understanding response.",
                "I do not feel comfortable discussing this with classmates.",
                "I would like to know how to arrange a counselling session.",
                "I need a safe space to discuss my feelings."
            ]
        ),
        (
            "Adjustment difficulties",
            "I am finding it emotionally difficult to adjust to college life.",
            [
                "The new environment has been overwhelming for me.",
                "I am struggling to become comfortable with the changes.",
                "I would like guidance from the student support team.",
                "I have been finding it difficult to settle into a routine.",
                "I would appreciate help adjusting to this transition."
            ]
        ),
        (
            "Burnout support request",
            "I have been feeling mentally exhausted and emotionally overwhelmed.",
            [
                "I find it difficult to relax even after completing my responsibilities.",
                "I would like to learn how to manage these feelings.",
                "I have been struggling to maintain my usual routine.",
                "I think professional support could be helpful.",
                "I would appreciate an opportunity to speak with a counsellor."
            ]
        ),
        (
            "Difficulty managing emotions",
            "I am finding it difficult to manage my emotions during stressful situations.",
            [
                "I sometimes feel overwhelmed by my reactions.",
                "I would like to develop healthier ways to cope.",
                "This has been affecting my personal well-being.",
                "I would appreciate guidance from a trained professional.",
                "I want to understand how to handle these feelings."
            ]
        ),
        (
            "Social interaction difficulties",
            "I feel uncomfortable interacting with people and making new friends.",
            [
                "I often avoid social situations because I feel nervous.",
                "I would like help becoming more comfortable around others.",
                "This has made me feel isolated.",
                "I would appreciate a conversation with a counsellor.",
                "I want to understand what support services are available."
            ]
        ),
        (
            "Confidential emotional support",
            "I would like to discuss a personal emotional concern confidentially.",
            [
                "I am not comfortable sharing this matter with classmates.",
                "I would prefer to speak with an authorised counsellor.",
                "I want my personal concerns to be handled sensitively.",
                "I would appreciate information about private counselling.",
                "I need someone who can listen without judging me."
            ]
        ),
        (
            "Academic pressure related stress",
            "The pressure of balancing college responsibilities has been affecting my emotional well-being.",
            [
                "I have been feeling overwhelmed rather than simply struggling with a subject.",
                "I would like support in managing the stress I am experiencing.",
                "The pressure has been affecting my sleep and routine.",
                "I want to discuss my feelings with a counsellor.",
                "I would appreciate help maintaining my emotional well-being."
            ]
        ),
        (
            "Personal well-being support",
            "I have noticed changes in my emotional well-being and would like support.",
            [
                "I have not been feeling emotionally settled recently.",
                "I would like to understand what support is available.",
                "I would prefer to speak with a trained counsellor.",
                "I find it difficult to handle these feelings alone.",
                "I would appreciate a private discussion."
            ]
        )
    ],

    "financial_assistance": [
        (
            "Scholarship application support",
            "I need guidance about applying for a scholarship offered to college students.",
            [
                "I would like to know how to begin the application.",
                "Please explain the application procedure.",
                "I need information about the documents required.",
                "I would like to know the application deadline.",
                "Could the finance office guide me through the process?"
            ]
        ),
        (
            "Fee payment difficulty",
            "My family is facing financial difficulties and I may not be able to pay my semester fees on time.",
            [
                "I would like to discuss possible financial assistance.",
                "The payment deadline is approaching.",
                "I need guidance about available fee support.",
                "Could the college explain the options available?",
                "I would appreciate help from the student finance office."
            ]
        ),
        (
            "Financial aid request",
            "I would like to apply for financial assistance to continue my education.",
            [
                "My family is currently unable to manage the full education expenses.",
                "I want to know the procedure for requesting financial aid.",
                "Please tell me which supporting documents are required.",
                "I would like to understand the available assistance schemes.",
                "Could someone guide me through the application?"
            ]
        ),
        (
            "Scholarship eligibility query",
            "I am unsure whether I meet the eligibility requirements for a scholarship.",
            [
                "I would like clarification about the qualifying conditions.",
                "Please explain the academic requirements.",
                "I need to know whether family income is considered.",
                "Could the concerned office review the eligibility criteria?",
                "I would appreciate information before applying."
            ]
        ),
        (
            "Education loan guidance",
            "I need information about education loan options for my studies.",
            [
                "I would like to understand the loan application process.",
                "Please guide me about the documents generally required.",
                "I need information about available education financing options.",
                "Could someone direct me to the appropriate support office?",
                "I would like to understand the next steps."
            ]
        ),
        (
            "Fee deadline extension",
            "I need to request additional time to pay my semester fees.",
            [
                "I am currently unable to arrange the full amount before the deadline.",
                "Could the college explain its fee extension procedure?",
                "I would like to know how to submit an extension request.",
                "Please tell me whom I should contact.",
                "I would appreciate guidance before the due date."
            ]
        ),
        (
            "Financial documentation support",
            "I am confused about the documents required for a financial assistance application.",
            [
                "I want to make sure that I submit the correct paperwork.",
                "Could someone share the required document list?",
                "I would like clarification about income certificates.",
                "Please explain how supporting documents should be submitted.",
                "I need help completing the documentation."
            ]
        ),
        (
            "Scholarship renewal issue",
            "I am facing difficulties renewing my existing scholarship.",
            [
                "I would like to know the renewal procedure.",
                "Please clarify the documents needed for renewal.",
                "I need information about the renewal deadline.",
                "Could someone explain why my renewal request is pending?",
                "I would appreciate help from the scholarship office."
            ]
        ),
        (
            "Hostel fee assistance",
            "I am finding it difficult to arrange the money required to pay my hostel fees.",
            [
                "I would like to know whether hostel fee assistance is available.",
                "Could the college explain the support options?",
                "I need guidance about requesting financial help.",
                "The payment deadline is approaching.",
                "I would appreciate assistance from the concerned office."
            ]
        ),
        (
            "Financial aid application status",
            "I would like to know the status of my submitted financial assistance application.",
            [
                "I have already completed the application process.",
                "I have not received an update about the application.",
                "Could someone check whether my request is being processed?",
                "I would appreciate an update from the finance office.",
                "Please guide me about the next steps."
            ]
        ),
        (
            "Fee concession request",
            "I want to understand the process for applying for a fee concession.",
            [
                "My family circumstances make it difficult to pay the full fees.",
                "Could someone explain the concession eligibility criteria?",
                "I would like to know which documents are needed.",
                "Please guide me about submitting the request.",
                "I would appreciate information about the available policy."
            ]
        ),
        (
            "Emergency financial assistance",
            "My family has experienced an unexpected financial problem and I need educational support.",
            [
                "The situation may affect my ability to continue my studies.",
                "I would like to know whether emergency assistance is available.",
                "Could someone explain how to request urgent financial support?",
                "I need guidance from the student finance office.",
                "I would appreciate information about the next steps."
            ]
        ),
        (
            "Scholarship payment delay",
            "My approved scholarship amount has not been credited yet.",
            [
                "I would like to know whether the payment has been processed.",
                "Could someone check the status of the scholarship disbursement?",
                "I have not received the expected scholarship amount.",
                "Please guide me about reporting a delayed payment.",
                "I would appreciate an update from the scholarship office."
            ]
        ),
        (
            "Financial support eligibility",
            "I need guidance about the financial support schemes offered by the institution.",
            [
                "I would like to know which schemes are currently available.",
                "Please explain the eligibility conditions.",
                "Could someone guide me about choosing a suitable scheme?",
                "I need information about the application procedure.",
                "I would appreciate help from the concerned department."
            ]
        ),
        (
            "Installment payment request",
            "I would like to ask whether my college fees can be paid in installments.",
            [
                "Paying the full amount at once is difficult for my family.",
                "Could the college explain its installment policy?",
                "I would like to know how to request installment payments.",
                "Please tell me whether approval is required.",
                "I would appreciate guidance about the payment schedule."
            ]
        )
    ],

    "other": [
        (
            "Student identity card issue",
            "I am facing a problem with my student identity card.",
            [
                "The card is damaged and needs replacement.",
                "My identity card is not being recognised.",
                "I need guidance about getting a duplicate card.",
                "Could someone explain the replacement procedure?",
                "I would like to contact the office responsible for student cards."
            ]
        ),
        (
            "College event registration",
            "I need help with the registration process for a college event.",
            [
                "I am unable to complete the registration form.",
                "I would like to know the registration deadline.",
                "Could someone explain how to register?",
                "I need information about the event participation process.",
                "Please direct me to the event organising team."
            ]
        ),
        (
            "Administrative process query",
            "I need clarification about an administrative process at the college.",
            [
                "I am unsure about the steps involved.",
                "Could someone direct me to the responsible office?",
                "I would like to know which form needs to be submitted.",
                "Please explain the procedure I should follow.",
                "I would appreciate guidance from the administration."
            ]
        ),
        (
            "Document verification support",
            "I need assistance with the verification of my college documents.",
            [
                "I would like to know where the verification takes place.",
                "Could someone explain the verification procedure?",
                "I need to know which documents I should bring.",
                "Please tell me how long the process usually takes.",
                "I would appreciate guidance from the administrative office."
            ]
        ),
        (
            "Transport facility query",
            "I have a question regarding the college transportation facility.",
            [
                "I would like information about available bus routes.",
                "Could someone explain the transport registration process?",
                "I need clarification about the bus schedule.",
                "Please guide me about the transport office.",
                "I would like to know whom to contact about route information."
            ]
        ),
        (
            "Library service complaint",
            "I am facing an issue while using the college library services.",
            [
                "I am unable to access a library service.",
                "Could someone explain the procedure for resolving this issue?",
                "I would like to report a problem with the library facility.",
                "Please direct me to the library staff responsible.",
                "I need help understanding the library rules."
            ]
        ),
        (
            "Certificate request",
            "I need information about obtaining an official college certificate.",
            [
                "Could someone explain the certificate application procedure?",
                "I would like to know which documents are required.",
                "Please tell me where the application should be submitted.",
                "I need clarification about the collection process.",
                "I would appreciate guidance from the administration office."
            ]
        ),
        (
            "Timetable information request",
            "I need clarification regarding a change in my class timetable.",
            [
                "I would like to confirm the updated class timings.",
                "Could someone direct me to the latest timetable?",
                "I am unsure where timetable changes are announced.",
                "Please tell me whom to contact for confirmation.",
                "I need information about the revised schedule."
            ]
        ),
        (
            "College portal issue",
            "I am having trouble accessing a service on the college portal.",
            [
                "The portal is not displaying the required information.",
                "I would like guidance about reporting this technical issue.",
                "Could someone direct me to the portal support team?",
                "I am unable to access a particular student service.",
                "Please explain how this issue can be reported."
            ]
        ),
        (
            "Event participation query",
            "I need information about participating in an upcoming college event.",
            [
                "I would like to know the participation requirements.",
                "Could someone share the event schedule?",
                "I need clarification about the registration process.",
                "Please direct me to the event organisers.",
                "I would appreciate information about participation."
            ]
        ),
        (
            "Administrative office guidance",
            "I am unsure which administrative office handles my concern.",
            [
                "Could someone help me identify the correct department?",
                "I would like to avoid submitting my request to the wrong office.",
                "Please guide me towards the appropriate administrative team.",
                "I need information about where to submit my enquiry.",
                "I would appreciate clarification about the office responsibilities."
            ]
        ),
        (
            "Document submission query",
            "I need clarification about the process for submitting college documents.",
            [
                "I would like to know where the documents should be submitted.",
                "Could someone explain the accepted submission methods?",
                "I need information about the submission deadline.",
                "Please tell me whether an online submission is available.",
                "I would appreciate guidance about the procedure."
            ]
        ),
        (
            "Campus facility information",
            "I would like information about a general facility available on campus.",
            [
                "Could someone tell me where the facility is located?",
                "I need to know the timings of the facility.",
                "Please guide me about the rules for using it.",
                "I would appreciate information from the concerned office.",
                "Could someone direct me to the appropriate campus service?"
            ]
        ),
        (
            "Student service request",
            "I need assistance with a general student service provided by the college.",
            [
                "I am unsure how to access this service.",
                "Could someone explain the steps involved?",
                "Please direct me to the team responsible for this service.",
                "I would like to know the applicable procedure.",
                "I need clarification before submitting my request."
            ]
        ),
        (
            "General college enquiry",
            "I have a college-related question that does not fit into the available categories.",
            [
                "I am unsure which department can answer my question.",
                "Could someone direct me to the appropriate office?",
                "I would appreciate help identifying the correct contact.",
                "Please guide me about where to submit this enquiry.",
                "I need clarification about the relevant college procedure."
            ]
        )
    ]
}


REQUEST_VARIATIONS = {
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

def generate_category_records(category):
    scenarios = IMPROVED_SCENARIOS[category]
    variations = REQUEST_VARIATIONS[category]

    if len(scenarios) != 15:
        raise ValueError(f"{category}: expected 15 scenarios")

    if len(variations) != 4:
        raise ValueError(f"{category}: expected 4 request variations")

    records = []

    for title, scenario, contexts in scenarios:

        if len(contexts) != 5:
            raise ValueError(
                f"{category} - {title}: expected 5 contexts, found {len(contexts)}"
            )

        for context in contexts:
            for variation in variations:

                description = f"{scenario} {context} {variation}"

                records.append({
                    "title": title,
                    "description": description,
                    "category": category,
                    "data_source": "synthetic"
                })

    if len(records) != 300:
        raise ValueError(
            f"{category}: expected 300, generated {len(records)}"
        )

    descriptions = [record["description"] for record in records]

    if len(descriptions) != len(set(descriptions)):
        raise ValueError(f"{category}: duplicate descriptions detected")

    random.shuffle(records)

    return records



def main():

    if not V2_PATH.exists():
        raise FileNotFoundError(
            f"V2 dataset not found: {V2_PATH}"
        )

    old_df = pd.read_csv(V2_PATH)

    required_columns = {
        "title",
        "description",
        "category",
        "data_source"
    }

    if not required_columns.issubset(old_df.columns):
        raise ValueError("V2 dataset has missing required columns.")

    # Preserve the three approved categories.
    preserved_df = old_df[
        old_df["category"].isin(KEEP_CATEGORIES)
    ].copy()

    preserved_counts = preserved_df["category"].value_counts()

    for category in KEEP_CATEGORIES:
        if preserved_counts.get(category, 0) != RECORDS_PER_CATEGORY:
            raise ValueError(
                f"Expected 300 existing records for {category}"
            )

    # Generate improved records for the other three categories.
    improved_records = []

    for category in IMPROVED_SCENARIOS:
        records = generate_category_records(category)
        improved_records.extend(records)

        print(category, ":", len(records), "new records generated")

    improved_df = pd.DataFrame(improved_records)

    # Combine preserved and improved records.
    final_df = pd.concat(
        [preserved_df, improved_df],
        ignore_index=True
    )

    # Shuffle the complete dataset.
    final_df = final_df.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    # Validation checks.
    if final_df.isnull().any().any():
        raise ValueError("Missing values detected.")

    if final_df["description"].str.strip().eq("").any():
        raise ValueError("Blank descriptions detected.")

    if final_df["description"].duplicated().any():
        raise ValueError("Duplicate descriptions detected.")

    if len(final_df) != 1800:
        raise ValueError(
            f"Expected 1800 records, found {len(final_df)}"
        )

    category_counts = final_df["category"].value_counts()

    for category in list(KEEP_CATEGORIES) + list(IMPROVED_SCENARIOS):
        if category_counts.get(category, 0) != 300:
            raise ValueError(
                f"Incorrect record count for {category}"
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

    print("\n========== V2.1 GENERATION SUMMARY ==========")
    print("Total records:", len(final_df))
    print("\nCategory distribution:")
    print(category_counts.sort_index())
    print("\nUnique descriptions:", final_df["description"].nunique())
    print("Unique titles:", final_df["title"].nunique())

    print("\nSaved successfully:")
    print(OUTPUT_PATH)

    print("\nSample records:")
    print(
        final_df.sample(
            12,
            random_state=42
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()
