"""Answer generator — generates a text answer from a prompt using local Gemma 4."""
from __future__ import annotations

import ollama

MODELS = ["gemma4:e4b", "gemma4:26b"]


async def generate_answer(prompt: str) -> str:
    """
    Generate an answer from a fully-built prompt string.

    Args:
        prompt: The complete prompt (built by prompt_builder.py).

    Returns:
        The model's text answer, or an error string if all models fail.
    """
    client = ollama.AsyncClient(host="http://localhost:11434")

    for model in MODELS:
        try:
            response = await client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"] or ""
        except Exception as e:
            print(f"[answer_generator] {model} error: {e}, trying next model...")
            continue

    return "Sorry, I was unable to generate an answer at this time."
