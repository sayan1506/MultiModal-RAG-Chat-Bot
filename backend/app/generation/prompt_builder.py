"""
Prompt builder — converts retrieved context into a prompt for Gemini.
"""

from typing import List


def build_prompt(
    query: str,
    retrieved_context: List[dict],
) -> str:
    context_parts = []

    for i, item in enumerate(retrieved_context, start=1):
        source = item.content

        context_parts.append(
            f"""
Source {i}
Type: {item.source}
Content:
{source}
"""
        )

    context_text = "\n".join(context_parts)

    prompt = f"""
You are an expert multimodal RAG assistant.

Answer the user's question using ONLY the provided context.

If the answer is not present in the context,
say that the information could not be found.

Question:
{query}

Context:
{context_text}

Provide a detailed answer.
"""

    return prompt