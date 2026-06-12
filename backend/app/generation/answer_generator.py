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


async def fuse_answers(
    query: str,
    kg_answer: str,
    visual_answer: str,
) -> str:
    """
    MegaRAG paper Section 3.3 — Stage 2 fusion.
    Integrates KG answer and visual answer into a single comprehensive response.

    Args:
        query:         The original user question.
        kg_answer:     Intermediate answer from knowledge graph (Stage 1).
        visual_answer: Intermediate answer from page images (Stage 1).

    Returns:
        A final fused answer string.
    """
    from app.ingestion.github_client import call_gpt4o_mini_async

    # If one answer is empty, return the other directly
    if not kg_answer and not visual_answer:
        return "I was unable to find relevant information to answer your question."
    if not kg_answer:
        return visual_answer
    if not visual_answer:
        return kg_answer

    fusion_prompt = f"""You are synthesizing two independent answers into one comprehensive response.

You have two answers to the same question — one from a knowledge graph and
one from document page images. Your task is to integrate them into a single,
complete answer that:
- Includes all relevant information from both sources
- Resolves any conflicts using the knowledge graph as the primary source
  (unless the visual evidence clearly contradicts it)
- Uses markdown headers to organize sections where appropriate
- Lists up to 3 key reference sources at the end

Question: {query}

Answer from Knowledge Graph:
{kg_answer}

Answer from Document Images:
{visual_answer}

Provide the integrated final answer:"""

    return await call_gpt4o_mini_async(
        fusion_prompt,
        max_tokens=2000,
        temperature=0.0,
    )
