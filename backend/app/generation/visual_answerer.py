"""Visual answerer — answers questions from page screenshots.

Uses GPT-4o-mini vision (paper-faithful) with Gemma4 as fallback.
Caps at top_m_pages images (paper default: 6).
"""
from __future__ import annotations

from app.config import settings
from app.ingestion.github_client import call_gpt4o_mini_vision_async


async def answer_from_images(query: str, page_images: list[dict]) -> str:
    """
    Answer the user query using retrieved document page screenshots.

    Args:
        query:       The user's question.
        page_images: List of dicts from ImageFetcher.fetch_pages().
                     Each dict has: page_number (int), image_bytes (bytes).

    Returns:
        A string answer, or "" if no images or all models fail.
    """
    if not page_images:
        return ""

    # Cap at top_m_pages (paper default: 6)
    images_to_use = page_images[:settings.top_m_pages]
    image_bytes_list = [img["image_bytes"] for img in images_to_use]

    prompt = (
        "You are answering a question based solely on the document pages shown.\n"
        "Carefully examine all provided pages for relevant information.\n"
        "If the answer is not visible in the pages, say so clearly.\n\n"
        f"Question: {query}"
    )

    return await call_gpt4o_mini_vision_async(
        prompt=prompt,
        image_bytes_list=image_bytes_list,
        max_tokens=1500,
        temperature=0.0,
    )
