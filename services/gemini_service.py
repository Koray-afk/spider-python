import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=gemini_api_key)

def analyze_text(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt)

    return response.text