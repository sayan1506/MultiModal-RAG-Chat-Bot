"""KG answerer — answers questions from the Neo4j knowledge graph context."""
from __future__ import annotations

import json

import ollama

MODELS = ["gemma4:e4b", "gemma4:26b"]


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
        # No graph data — skip rather than sending an empty context prompt
        return ""

    # Truncate large graphs to stay within context window
    context = json.dumps(subgraph, indent=2)[:4000]

    prompt = f"""You are an AI assistant answering questions using a knowledge graph.

Knowledge Graph Context (entities and relationships from the document):
{context}

User Question: {query}

Instructions:
- Answer using ONLY the knowledge graph context above.
- Be concise and factual.
- If the context does not contain enough information, say:
  "The knowledge graph does not contain enough information to answer this."
- Do not invent information not present in the graph."""

    client = ollama.AsyncClient(host="http://localhost:11434")

    for model in MODELS:
        try:
            response = await client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"] or ""
        except Exception as e:
            print(f"[kg_answerer] {model} error: {e}, trying next model...")
            continue

    print("[kg_answerer] All models failed.")
    return ""
