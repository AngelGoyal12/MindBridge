
from ai_service.gemini_service import test_gemini_connection

try:
    result = test_gemini_connection()
    print(result)
except Exception as e:
    print("Gemini connection failed:", e)
