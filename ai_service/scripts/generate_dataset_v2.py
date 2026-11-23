
import pandas as pd
import random
from pathlib import Path
from itertools import product

random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BASE_DIR / "data" / "raw" / "mindbridge_synthetic_cases_v2.csv"

RECORDS_PER_CATEGORY = 300

# Each scenario has a relevant title and a realistic student problem.
SCENARIOS = {

    "academic_support": [
        ("Programming learning difficulty", "I am struggling to understand programming concepts."),
        ("Data structures assistance", "I find data structures such as trees and linked lists difficult to understand."),
        ("Database coursework support", "I am having difficulty understanding database management and SQL queries."),
        ("Operating systems guidance", "I am finding operating systems concepts difficult to learn."),
        ("Computer networks support", "I need help understanding computer networks and their protocols."),
        ("Mathematics study assistance", "I am struggling with mathematical concepts covered in my coursework."),
        ("Artificial intelligence guidance", "I am having trouble understanding artificial intelligence topics."),
        ("Coding assignment difficulty", "I am unable to complete my programming assignments independently."),
        ("Examination preparation support", "I am finding it difficult to prepare effectively for my semester examinations."),
        ("Academic project guidance", "I am facing difficulties while developing my academic project."),
        ("Study schedule assistance", "I am unable to manage my study schedule effectively."),
        ("Assignment requirement clarification", "I am confused about the requirements of my current assignment."),
        ("Practical subject assistance", "I am struggling to understand the practical exercises taught in my course."),
        ("Faculty academic guidance", "I need academic guidance regarding the subjects I am currently studying."),
        ("Learning improvement support", "I understand classroom explanations but struggle to apply the concepts during practice.")
    ],

    "hostel_issue": [
        ("Water supply complaint", "There is an irregular water supply in my hostel room."),
        ("Room cleanliness issue", "My hostel room is not being cleaned properly."),
        ("Bathroom maintenance request", "The bathroom in my hostel requires maintenance."),
        ("Electrical repair request", "There is an electrical problem with the lights in my hostel room."),
        ("Room door lock issue", "The lock on my hostel room door is not working properly."),
        ("Furniture repair request", "The furniture provided in my hostel room is damaged."),
        ("Internet connectivity issue", "The hostel Wi-Fi connection is frequently unavailable."),
        ("Laundry service complaint", "I am facing problems with the hostel laundry service."),
        ("Drinking water facility issue", "The drinking water facility on my hostel floor is not working properly."),
        ("Room ventilation complaint", "My hostel room has insufficient ventilation."),
        ("Ceiling fan maintenance", "The ceiling fan in my room is not functioning correctly."),
        ("Hostel common area complaint", "The common areas in my hostel are not being maintained properly."),
        ("Washroom hygiene complaint", "The shared washroom on my floor requires proper cleaning."),
        ("Pest control request", "There is a pest problem inside my hostel room."),
        ("Hostel maintenance follow-up", "A maintenance problem in my hostel has not yet been resolved.")
    ],

    "ragging_bullying": [
        ("Repeated teasing complaint", "Some students repeatedly make insulting comments about me."),
        ("Intimidation by students", "I feel intimidated by a group of students in my college."),
        ("Unwanted senior interaction", "Some seniors are pressuring me to do things that make me uncomfortable."),
        ("Online bullying complaint", "I am receiving insulting and hurtful messages from other students."),
        ("Public humiliation concern", "Some students deliberately embarrass me in front of others."),
        ("Threatening behaviour report", "I have received threats from another student."),
        ("Repeated harassment concern", "A student continues to disturb me even after I asked them to stop."),
        ("Social exclusion complaint", "Some classmates deliberately exclude and target me during college activities."),
        ("Inappropriate comments report", "I am uncomfortable with repeated personal comments made by other students."),
        ("Pressure from senior students", "Some senior students are forcing me to follow unreasonable instructions."),
        ("Physical intimidation report", "Another student has physically intimidated me on campus."),
        ("Group bullying concern", "A group of students regularly targets me and makes me feel unsafe."),
        ("Harassment during college activities", "I am facing unwanted behaviour from students during college activities."),
        ("Repeated mocking complaint", "Other students repeatedly mock me because of my personal choices."),
        ("Confidential bullying report", "I want to report repeated bullying without sharing my identity unnecessarily.")
    ],

    "emotional_support": [
        ("Academic stress support", "I have been feeling overwhelmed because of academic pressure."),
        ("Anxiety support request", "I have been experiencing anxiety that is affecting my daily routine."),
        ("Loneliness and isolation", "I have been feeling lonely and disconnected from other students."),
        ("Motivation difficulties", "I have been finding it difficult to stay motivated with my studies."),
        ("Personal stress support", "Personal problems have been causing me considerable emotional stress."),
        ("Adjustment difficulties", "I am finding it difficult to adjust to college life."),
        ("Emotional distress support", "I have been feeling emotionally disturbed and need someone to talk to."),
        ("Confidence improvement support", "I have been struggling with low confidence in social and academic situations."),
        ("Homesickness support", "I have been missing my family and finding it difficult to stay away from home."),
        ("Relationship stress support", "A personal relationship problem has been affecting my emotional well-being."),
        ("Counselling appointment request", "I would like to speak with a counsellor about some personal concerns."),
        ("Difficulty managing emotions", "I am finding it difficult to manage my emotions during stressful situations."),
        ("Social interaction difficulties", "I feel uncomfortable interacting with people and making new friends."),
        ("Burnout support request", "I have been feeling mentally exhausted because of my daily responsibilities."),
        ("Confidential emotional support", "I would like to discuss a personal emotional concern in a confidential setting.")
    ],

    "financial_assistance": [
        ("Scholarship application support", "I need guidance regarding scholarships available to students."),
        ("Fee payment difficulty", "My family is facing financial difficulties and I may not be able to pay my fees on time."),
        ("Financial aid request", "I would like to apply for financial assistance to continue my education."),
        ("Scholarship eligibility query", "I am unsure whether I meet the eligibility requirements for a scholarship."),
        ("Education loan guidance", "I need information about education loan options for my studies."),
        ("Fee deadline extension", "I need to request additional time to pay my semester fees."),
        ("Financial documentation support", "I am confused about the documents required for financial assistance."),
        ("Scholarship renewal issue", "I am facing difficulties with the renewal of my scholarship."),
        ("Hostel fee assistance", "I am finding it difficult to arrange the money required for hostel fees."),
        ("Financial aid application status", "I would like to know the status of my financial assistance application."),
        ("Fee concession request", "I want to understand the process for applying for a fee concession."),
        ("Emergency financial assistance", "My family has experienced an unexpected financial problem and I need support."),
        ("Scholarship payment delay", "My approved scholarship amount has not been credited yet."),
        ("Financial support eligibility", "I need guidance about financial support schemes offered by the institution."),
        ("Installment payment request", "I would like to ask whether my college fees can be paid in installments.")
    ],

    "other": [
        ("Student identity card issue", "I am facing a problem with my student identity card."),
        ("College event registration", "I need help with the registration process for a college event."),
        ("Administrative process query", "I am confused about an administrative process at the college."),
        ("Document verification support", "I need assistance with the verification of my college documents."),
        ("Transport facility query", "I have a question regarding the college transportation facility."),
        ("Library service complaint", "I am facing an issue while using the college library services."),
        ("Certificate request", "I need information about obtaining an official college certificate."),
        ("Timetable information request", "I need clarification regarding a change in my class timetable."),
        ("College portal issue", "I am having trouble accessing a service on the college portal."),
        ("Event participation query", "I need information about participating in an upcoming college event."),
        ("Administrative office guidance", "I am unsure which administrative office handles my concern."),
        ("Document submission query", "I need clarification about the process for submitting college documents."),
        ("Campus facility information", "I would like information about a facility available on campus."),
        ("Student service request", "I need assistance with a general student service provided by the college."),
        ("General college enquiry", "I have a college-related question that does not fit into the available categories.")
    ]
}

# Additional context is category-specific.
# It adds detail to each scenario without changing its meaning.

CONTEXTS = {

    "academic_support": [
        "I have tried studying from my class notes but still need clarification.",
        "The difficulty is affecting my ability to complete coursework on time.",
        "I would benefit from additional explanations and practice material.",
        "I have already reviewed the lecture material but remain confused.",
        "I would like to know which learning resources I should use.",
        "The topic becomes difficult when I try to solve questions independently.",
        "I would appreciate guidance from the concerned faculty member.",
        "I need help identifying the concepts that I should revise first.",
        "I am looking for a way to improve my understanding of the subject.",
        "This issue has been affecting my academic progress.",
        "I would like to attend an additional doubt-clearing session.",
        "I need some direction before my next assessment.",
        "I have difficulty applying the theory to practical questions.",
        "Could the academic support team suggest an appropriate solution?",
        "I would like to discuss this concern with my department.",
        "I need help understanding the steps involved in solving these problems.",
        "I have been practising but my results are not improving.",
        "I would appreciate some structured academic guidance.",
        "I want to improve my performance in this subject.",
        "Please let me know how I can access academic support."
    ],

    "hostel_issue": [
        "This problem is affecting my daily routine in the hostel.",
        "I have already informed the hostel staff but the issue remains.",
        "Could the maintenance team inspect the affected area?",
        "I would appreciate a timely repair or maintenance visit.",
        "The issue has continued for several days.",
        "Other residents on my floor are also experiencing this problem.",
        "I would like to know when this complaint can be addressed.",
        "The facility is important for our everyday hostel activities.",
        "I have reported the problem to the warden.",
        "Please arrange an inspection by the concerned staff.",
        "The problem is causing inconvenience to hostel residents.",
        "I would like the hostel administration to look into this matter.",
        "The issue has not improved despite previous complaints.",
        "Could someone confirm when maintenance will be available?",
        "I request that the concerned department take appropriate action.",
        "This is making it difficult to use the hostel facility properly.",
        "I would appreciate an update about the maintenance request.",
        "The affected facility needs attention as soon as possible.",
        "Please guide me about the correct complaint procedure.",
        "I hope the hostel team can resolve this issue."
    ],

    "ragging_bullying": [
        "This behaviour has made me uncomfortable attending college.",
        "I do not feel comfortable handling this situation alone.",
        "I would like the matter to be handled sensitively.",
        "I am worried that the behaviour may continue.",
        "I need guidance about the college reporting procedure.",
        "I would prefer to discuss this with an authorised staff member.",
        "I am concerned about facing further harassment.",
        "The incidents have started affecting my sense of safety.",
        "I would appreciate a confidential discussion about this matter.",
        "I want the concerned authority to investigate the situation.",
        "I have been hesitant to report this because I fear retaliation.",
        "I would like to understand what support is available to me.",
        "The behaviour has happened more than once.",
        "I need help from someone who can handle student safety concerns.",
        "Please explain how I can report this incident safely.",
        "I would like my concern to be taken seriously.",
        "I am requesting appropriate support from the college authorities.",
        "I do not want this behaviour to happen to other students.",
        "I would appreciate protection from further unwanted contact.",
        "Please let me know the next steps for raising this concern."
    ],

    "emotional_support": [
        "I do not feel comfortable discussing this with my classmates.",
        "I would like to speak with someone who can listen without judging me.",
        "This has started affecting my everyday activities.",
        "I am looking for a safe space to discuss my feelings.",
        "I would appreciate guidance on available counselling services.",
        "I have not been able to manage this situation on my own.",
        "I would prefer a private conversation with a counsellor.",
        "I need support in understanding and managing these feelings.",
        "This concern has been difficult for me to talk about.",
        "I would like to know how I can arrange a counselling session.",
        "I am hoping to receive emotional support from the institution.",
        "I need someone to help me work through this situation.",
        "I would appreciate a patient and understanding response.",
        "I want to discuss this concern at a time convenient for me.",
        "I have been finding it difficult to focus on my routine.",
        "I would like to understand what support options are available.",
        "I am requesting guidance from the student support team.",
        "I would feel more comfortable discussing this privately.",
        "Please guide me towards an appropriate support service.",
        "I think speaking to a trained counsellor may help."
    ],

    "financial_assistance": [
        "I would like to understand the application procedure.",
        "Please tell me which documents I need to submit.",
        "I would appreciate guidance from the student finance office.",
        "I need to know whether any financial support scheme is available.",
        "Could someone explain the eligibility requirements?",
        "I would like to know the expected processing time.",
        "This financial difficulty is affecting my education plans.",
        "I want to understand the options available before the payment deadline.",
        "Please guide me about the next steps in the process.",
        "I would appreciate an update from the concerned department.",
        "I am willing to provide the required supporting documents.",
        "Could the institution explain its financial assistance policy?",
        "I need clarification about the scholarship conditions.",
        "I would like to know whom I should contact for help.",
        "Please let me know whether an extension can be requested.",
        "I am looking for a suitable financial support option.",
        "Could someone review my application and guide me?",
        "I would appreciate information about available student aid.",
        "I need assistance understanding the payment process.",
        "Please share the procedure for raising this request."
    ],

    "other": [
        "I am not sure which department handles this request.",
        "Could someone direct me to the appropriate office?",
        "I would appreciate clarification about the procedure.",
        "Please let me know whom I should contact.",
        "I have not been able to find the required information.",
        "Could the concerned staff help me resolve this matter?",
        "I would like to understand the steps involved.",
        "Please share the relevant information with me.",
        "I would appreciate an update regarding this request.",
        "I need assistance from the appropriate college department.",
        "Could someone explain the applicable college policy?",
        "I would like to know where this issue should be reported.",
        "Please guide me towards the correct student service.",
        "I need clarification before proceeding further.",
        "I would appreciate a response from the concerned team.",
        "Could you tell me how to submit this request?",
        "I am looking for the correct process to follow.",
        "Please help me understand the available options.",
        "I would like this concern to reach the appropriate department.",
        "Could someone provide the next steps?"
    ]
}


def generate_category_records(category):
    scenarios = SCENARIOS[category]
    contexts = CONTEXTS[category]

    combinations = list(product(scenarios, contexts))

    if len(combinations) < RECORDS_PER_CATEGORY:
        raise ValueError(
            f"Not enough combinations for category: {category}"
        )

    random.shuffle(combinations)

    records = []

    for (title, scenario), context in combinations[:RECORDS_PER_CATEGORY]:
        description = f"{scenario} {context}"

        records.append({
            "title": title,
            "description": description,
            "category": category,
            "data_source": "synthetic"
        })

    return records


def main():
    all_records = []

    print("\n========== DATASET GENERATION ==========\n")

    for category in SCENARIOS:
        category_records = generate_category_records(category)
        all_records.extend(category_records)

        print(
            category,
            ":",
            len(category_records),
            "records generated"
        )

    df = pd.DataFrame(all_records)

    # Shuffle records so categories are not grouped together.
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # Basic safety checks before saving.
    if df["description"].duplicated().any():
        raise ValueError("Duplicate descriptions detected!")

    if df.isnull().any().any():
        raise ValueError("Missing values detected!")

    if len(df) != 1800:
        raise ValueError("Unexpected total record count!")

    category_counts = df["category"].value_counts()

    if not all(category_counts.get(cat, 0) == 300 for cat in SCENARIOS):
        raise ValueError("Category distribution is incorrect!")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print("\n========== GENERATION SUMMARY ==========")
    print("Total records:", len(df))
    print("\nCategory distribution:")
    print(category_counts.sort_index())

    print("\nUnique descriptions:", df["description"].nunique())
    print("Unique titles:", df["title"].nunique())

    print("\nCSV saved successfully:")
    print(OUTPUT_PATH)

    print("\nSample records:")
    print(df.sample(10, random_state=42).to_string(index=False))


if __name__ == "__main__":
    main()
