import base64
from google import genai
from google.genai import types
from app.config import settings

import time

client = genai.Client(api_key=settings.gemini_api_key)


def embed_text(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return response.embeddings[0].values



def describe_image(image_bytes: bytes) -> str:
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash-lite"]

    for model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        "Describe this image briefly.",
                    ],
                )
                return response.text
            except Exception as e:
                err = str(e)
                if "503" in err or "UNAVAILABLE" in err:
                    print(f"{model} unavailable, retrying in {2**attempt}s...")
                    time.sleep(2 ** attempt)
                elif "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"{model} quota exhausted, trying next model...")
                    break  # skip retries, try next model
                else:
                    break  # 404 or other permanent error, skip immediately

    print("All Gemini vision models unavailable, falling back to text-only.")
    return ""

def embed_image(image_bytes: bytes) -> list[float]:
    description = describe_image(image_bytes)
    if not description:
        return []  # signals caller to use text-only path
    return embed_text(description)


def embed_text_and_image(text: str, image_bytes: bytes) -> list[float]:
    tv = embed_text(text)
    iv = embed_image(image_bytes)
    if not iv:
        return tv  # graceful text-only fallback
    avg = [(a + b) / 2 for a, b in zip(tv, iv)]
    norm = sum(x ** 2 for x in avg) ** 0.5
    return [x / norm for x in avg] if norm else avg