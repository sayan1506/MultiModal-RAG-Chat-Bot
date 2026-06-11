"""Visual answerer — answers questions from page screenshots using Gemma 4 vision."""
from __future__ import annotations

import ollama

MODELS = ["gemma4:e4b", "gemma4:26b"]


async def answer_from_images(query: str, page_images: list[dict]) -> str:
    """
    Send up to 3 page PNG screenshots to Gemma 4 and return an answer.

    Args:
        query:       The user's question.
        page_images: List of dicts from ImageFetcher.fetch_pages().
                     Each dict has keys: page_number (int),
                     image_bytes (bytes), image_url (str).

    Returns:
        A string answer, or "" if no images were provided or all models fail.
    """
    if not page_images:
        return ""

    # Cap at 3 images to stay within context limits
    images_to_use = page_images[:3]

    # Ollama vision: pass raw bytes in the images list of the message
    image_bytes_list = [img["image_bytes"] for img in images_to_use]

    prompt_text = (
        f"Answer this question using ONLY the document pages shown in the images.\n"
        f"If the answer is not visible in the pages, say so clearly.\n\n"
        f"Question: {query}"
    )

    client = ollama.AsyncClient(host="http://localhost:11434")

    for model in MODELS:
        try:
            response = await client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text,
                        "images": image_bytes_list,  # raw bytes — SDK handles encoding
                    }
                ],
            )
            return response["message"]["content"] or ""
        except Exception as e:
            print(f"[visual_answerer] {model} error: {e}, trying next model...")
            continue

    print("[visual_answerer] All models failed.")
    return ""
