from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=TOKEN
)

for model in client.models.list():
    print(model.name)