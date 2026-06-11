"""Query analyzer — decomposes user query into keywords and semantic concepts."""
from __future__ import annotations

import json
import re

import ollama

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """Analyze this search query for a RAG system.
Query: "{query}"
Return ONLY valid JSON — no markdown, no explanation, no code fences:
{{
  "low_level_keywords":  ["exact term1", "exact term2"],
  "high_level_concepts": ["semantic concept1", "semantic concept2"],
  "query_type": "factual|analytical|visual|comparative"
}}"""

# ---------------------------------------------------------------------------
# Models (primary → fallback)
# ---------------------------------------------------------------------------

MODELS = ["gemma4:e4b", "gemma4:26b"]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_query(query: str) -> dict:
    """
    Decompose a user query into retrieval-friendly components.

    Returns:
        low_level_keywords  — exact words to match in Neo4j entity labels
        high_level_concepts — broader semantic terms for Pinecone search
        query_type          — hint for generation layer
    """
    prompt = ANALYSIS_PROMPT.format(query=query)
    client = ollama.AsyncClient(host="http://localhost:11434")

    for model in MODELS:
        try:
            response = await client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},  # low temp for deterministic JSON
            )
            raw: str = response["message"]["content"]

            # Strip markdown fences if model added them anyway
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Try extracting the JSON object from surrounding text
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
            # JSON parse failed — try next model
            print(f"[query_analyzer] {model} returned non-JSON, trying next model...")

        except Exception as e:
            print(f"[query_analyzer] {model} error: {e}, trying next model...")
            continue

    # All models failed — keyword-split fallback
    print("[query_analyzer] All models failed, using keyword fallback.")
    return {
        "low_level_keywords":  query.split(),
        "high_level_concepts": [query],
        "query_type":          "factual",
    }
