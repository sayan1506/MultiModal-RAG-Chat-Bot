"""KG answerer — answers questions from the Neo4j knowledge graph context.

Uses GPT-4o-mini (paper-faithful) with Gemma4 as fallback.
"""
from __future__ import annotations

import json

from app.ingestion.github_client import call_gpt4o_mini_async


async def answer_from_kg(query: str, subgraph: dict) -> str:
    """
    Answer the user query using knowledge graph entities and relationships.

    Args:
        query:    The user's question.
        subgraph: Dict with {"nodes": [...], "links": [...]} from Neo4jRetriever.

    Returns:
        A string answer, or "" if the subgraph is empty or all models fail.
    """
    nodes = subgraph.get("nodes", [])
    if not nodes:
        return ""

    # Truncate large graphs to stay within 8k token limit for GitHub Models
    context = json.dumps(subgraph, indent=2)[:6000]

    prompt = f"""You are answering a question using a structured knowledge graph.

Knowledge Graph Context (entities and relationships from the document):
{context}

User Question: {query}

Instructions:
- Answer using ONLY the knowledge graph context above.
- Be factual and concise.
- Reference specific entities and relationships where relevant.
- If the context does not contain enough information, say:
  "The knowledge graph does not contain enough information to answer this."
- Do not invent information not present in the graph."""

    return await call_gpt4o_mini_async(
        prompt,
        max_tokens=1500,
        temperature=0.0,
    )
