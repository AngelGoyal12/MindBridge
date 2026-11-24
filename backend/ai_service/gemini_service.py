
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment")

client = genai.Client(api_key=api_key)


def test_gemini_connection():
    response = client.interactions.create(
        model="gemini-3.8-flash",
        input="Reply with exactly: Gemini connected successfully"
    )

    return response.output_text
