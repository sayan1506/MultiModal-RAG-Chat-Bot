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
    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    for model in models_to_try:
        for attempt in range(3):  # 3 retries per model
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
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    print(f"{model} unavailable, retrying in {2**attempt}s...")
                    time.sleep(2**attempt)  # exponential backoff: 1s, 2s, 4s
                else:
                    raise  # non-503 error, don't retry
    
    # All models failed — return empty string so pipeline continues
    print("All Gemini models unavailable, skipping image description.")
    return ""

def embed_image(image_bytes: bytes) -> list[float]:
    """Describe image with Gemini Vision then embed the description."""
    description = describe_image(image_bytes)
    return embed_text(description)


def embed_text_and_image(text: str, image_bytes: bytes) -> list[float]:
    """
    Average text embedding + image-description embedding.
    Returns a normalised joint vector for multimodal retrieval.
    """
    tv = embed_text(text)
    iv = embed_image(image_bytes)
    avg = [(a + b) / 2 for a, b in zip(tv, iv)]
    norm = sum(x ** 2 for x in avg) ** 0.5
    return [x / norm for x in avg] if norm else avg
