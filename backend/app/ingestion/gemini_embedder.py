import base64
from google import genai
from google.genai import types
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)


def embed_text(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return response.embeddings[0].values


def describe_image(image_bytes: bytes) -> str:
    """Send page PNG to Gemini Vision and get a text description."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            "Describe every visual element on this document page in detail: "
            "text, tables, charts, diagrams, headings, and figures. "
            "Be thorough — this description will be used for search.",
        ],
    )
    return response.text


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
