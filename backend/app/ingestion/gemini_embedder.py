from google import genai

from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)


def embed_text(text: str):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values