
import os
import json
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment")

client = Groq(api_key=api_key)

MODEL_NAME = "openai/gpt-oss-120b"


def test_groq_connection():
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: Groq connected successfully"
            }
        ],
    )

    return response.choices[0].message.content


def generate_coordinator_insights(statistics: dict):
    
    prompt = f"""
You are an AI assistant for MindBridge, a student support
and case management platform.

Analyze these anonymized coordinator dashboard statistics:

{json.dumps(statistics, indent=2)}

Generate insights under these headings:

1. Case Trends
2. Workload Analysis
3. Attention Required
4. Actionable Recommendations

Strict rules:

- Use only the statistics provided.
- Distinguish active cases from closed cases.
- Do not describe closed cases as active.
- Do not assume a case is delayed or stalled without duration data.
- Do not invent staff names, assignments, deadlines or events.
- Do not claim historical trends from a single snapshot.
- Mention overdue tasks using their actual count.
- Recommendations must be practical and based on available data.
- Clearly mention when additional information is required.
- Do not identify individual students.
- All suggestions are advisory, not automatic decisions.

Return readable plain text with clear headings and bullet points.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You generate privacy-conscious, evidence-based coordinator insights."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_completion_tokens=800,
    )

    return response.choices[0].message.content


def generate_case_action_plan(case_metadata: dict):

    prompt = f"""
You are an AI assistant for MindBridge, a student support
and case management platform.

Generate a practical action plan using only this anonymized case metadata:

{json.dumps(case_metadata, indent=2)}

Return a JSON object in exactly this format:

{{
    "action_plan": [
        {{
            "title": "Short action title",
            "description": "What action should be taken",
            "reason": "Why this action is relevant"
        }}
    ],
    "additional_information_needed": [
        "Information needed before taking further action"
    ]
}}


Strict rules:
- Use only the case metadata provided.
- Do not assume that any counselling session, meeting,
  intervention or support activity has taken place.
- Do not assume that the student has received any service.
- Do not suggest case closure activities unless the case
  status explicitly supports closure.
- Do not suggest contacting the student or collecting
  feedback unless the required consent and authorization
  are confirmed separately.
- Do not invent deadlines, review intervals or events.
- Do not assume urgency, risk or student satisfaction.
- Do not invent staff names or task assignments.
- If category and status are insufficient to recommend
  specific actions, clearly state what information is needed.
- Prefer coordinator review and information verification
  over unsupported action recommendations.
- Suggestions are advisory and require coordinator approval.
- Return valid JSON only. Do not use Markdown code fences.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate privacy-conscious, evidence-based "
                    "case action plans. Always return valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_completion_tokens=1000,
    )

    result = response.choices[0].message.content

    return json.loads(result)
