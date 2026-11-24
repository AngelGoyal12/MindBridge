
from ai_service.groq_service import test_groq_connection

try:
    result = test_groq_connection()
    print(result)
except Exception as e:
    print("Groq connection failed:", e)
