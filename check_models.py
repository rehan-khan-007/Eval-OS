import os
import httpx
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

response = httpx.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

models = response.json().get("data", [])

print(f"Found {len(models)} models. Filtering for Gemini and Claude Haiku...\n")
for model in models:
    mid = model.get("id", "")
    if "gemini" in mid and "flash" in mid:
        print(f"Gemini Flash ID: {mid}")
    if "haiku" in mid and "claude" in mid:
        print(f"Claude Haiku ID: {mid}")
