
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMMA_MODEL")

if api_key and api_key.strip():
    print("SUCCESS: API key loaded securely!")
    print("Model:", model)
else:
    print("ERROR: API key not found. Check .env file.")
