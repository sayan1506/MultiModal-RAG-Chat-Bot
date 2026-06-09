"""
Answer generator using Gemini.
"""

from google import genai

from app.config import settings

client = genai.Client(
    api_key=settings.gemini_api_key
)


async def generate_answer(
    prompt: str,
) -> str:

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt,
    )

    return response.text