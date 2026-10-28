
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load API credentials securely
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")

if not api_key:
    raise ValueError("API key missing! Check your .env file.")

# Connect to Google Gemma 4
client = genai.Client(api_key=api_key)

print("Connecting to Gemma 4...")

try:
    response = client.models.generate_content(
        model=model_name,
        contents=(
            "You are BrandPilot AI, an Instagram marketing manager. "
            "Generate an attractive Instagram caption for a Pakistani "
            "clothing brand selling an embroidered pink kurta for "
            "Rs. 2800. Include 5 hashtags and a call to action. "
            "Do not invent discounts or product specifications."
        )
    )

    print("\nSUCCESS! BrandPilot AI is connected!")
    print("\nGenerated Instagram Caption:\n")
    print(response.text)

except Exception as error:
    print("\nAI connection failed!")
    print("Error type:", type(error).__name__)
    print("Check model availability, API permissions, quota, or internet connection.")
