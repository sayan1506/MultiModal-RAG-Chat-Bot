"""Gemini embedder — text embeddings via Gemini API, image description via Ollama."""
from __future__ import annotations

import ollama as _ollama
from google import genai

from app.config import settings

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

# Gemini client — used ONLY for embed_text() (embedContent endpoint)
_gemini_client = genai.Client(api_key=settings.gemini_api_key)

# Ollama client — used for describe_image() (vision, no quota)
_ollama_client = _ollama.Client(host="http://localhost:11434")

# Ollama model preference order
_OLLAMA_MODELS = ["gemma4:e4b", "gemma4:26b"]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """
    Generate a 3072-dim embedding vector for a text string.

    Uses Gemini embedding-001 — must stay on Gemini to match the existing
    Pinecone index dimension (3072). Do NOT move this to Ollama.
    """
    response = _gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return response.embeddings[0].values


def describe_image(image_bytes: bytes) -> str:
    """
    Generate a text description of a page PNG using Gemma 4 vision locally.

    Uses Ollama — zero API quota, no rate limits.

    Args:
        image_bytes: Raw PNG bytes of a document page.

    Returns:
        A text description of the page content, or "" if all models fail.
    """
    for model in _OLLAMA_MODELS:
        try:
            response = _ollama_client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Describe this document page briefly. "
                            "Focus on: text content, headings, key terms, "
                            "tables, charts, and diagrams present on the page."
                        ),
                        "images": [image_bytes],  # raw bytes — SDK handles encoding
                    }
                ],
            )
            result = response["message"]["content"] or ""
            if result:
                return result
        except Exception as e:
            print(f"[describe_image] {model} error: {e}, trying next model...")
            continue

    print("[describe_image] All Ollama models failed, returning empty.")
    return ""


def embed_image(image_bytes: bytes) -> list[float]:
    """
    Embed a page image by describing it first, then embedding the description.

    Returns [] if description fails — caller should fall back to text-only path.
    """
    description = describe_image(image_bytes)
    if not description:
        return []
    return embed_text(description)


def embed_text_and_image(text: str, image_bytes: bytes) -> list[float]:
    """
    Produce a combined embedding by averaging text and image embeddings.

    Falls back to text-only if image description fails.
    """
    tv = embed_text(text)
    iv = embed_image(image_bytes)

    if not iv:
        return tv  # graceful text-only fallback

    avg = [(a + b) / 2 for a, b in zip(tv, iv)]
    norm = sum(x ** 2 for x in avg) ** 0.5
    return [x / norm for x in avg] if norm else avg
