"""Query analyzer — decomposes user query into keywords and semantic concepts."""
from __future__ import annotations

import json
import re

from google import genai
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

ANALYSIS_PROMPT = """Analyze this search query for a RAG system.

Query: "{query}"

Return ONLY valid JSON — no markdown, no explanation:
{{
  "low_level_keywords":  ["exact term1", "exact term2"],
  "high_level_concepts": ["semantic concept1", "semantic concept2"],
  "query_type": "factual|analytical|visual|comparative"
}}"""


async def analyze_query(query: str) -> dict:
    """
    Returns:
        low_level_keywords  — exact words to match in Neo4j entity labels
        high_level_concepts — broader semantic terms for Pinecone search
        query_type          — hint for generation layer
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[ANALYSIS_PROMPT.format(query=query)],
        )
        raw = response.text
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"Query analysis failed: {e}")

    # Fallback — split the raw query into keywords
    return {
        "low_level_keywords":  query.split(),
        "high_level_concepts": [query],
        "query_type":          "factual",
    }