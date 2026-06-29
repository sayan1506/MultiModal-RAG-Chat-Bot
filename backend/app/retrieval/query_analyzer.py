"""Query analyzer — extracts low-level and high-level keywords from user query.

Low-level keywords  → entity store retrieval (specific named entities)
High-level keywords → relation store retrieval (broad concepts/themes)

Model: GitHub GPT-4o-mini → Gemma4 fallback
"""
from __future__ import annotations

import json
import re

from app.ingestion.github_client import call_gpt4o_mini_async

_ANALYSIS_PROMPT = """Analyze the following user query for a document retrieval system.

Extract two types of keywords:
1. low_level_keywords: Specific named entities, technical terms, people,
   organizations, or precise concepts (for entity-level graph retrieval)
2. high_level_keywords: Broader themes, topics, or conceptual categories
   (for relation-level graph retrieval)

User query: {query}

Return ONLY this JSON (no markdown, no explanation):
{{
  "low_level_keywords": ["keyword1", "keyword2"],
  "high_level_keywords": ["theme1", "theme2"]
}}"""

_EMPTY_ANALYSIS = {
    "low_level_keywords": [],
    "high_level_keywords": [],
}


async def analyze_query(query: str) -> dict:
    """
    Extract low-level and high-level keywords from a user query.

    Returns:
        Dict with "low_level_keywords" and "high_level_keywords" lists.
        Falls back to treating the whole query as low-level keywords on failure.
    """
    prompt = _ANALYSIS_PROMPT.format(query=query)
    raw = await call_gpt4o_mini_async(prompt, max_tokens=200, temperature=0.0)

    if not raw:
        # Minimal fallback: split query into words as keywords
        words = [w.strip(".,?!") for w in query.split() if len(w) > 3]
        return {"low_level_keywords": words[:5], "high_level_keywords": []}

    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        result = json.loads(raw)
        if "low_level_keywords" in result and "high_level_keywords" in result:
            return result
    except json.JSONDecodeError:
        pass

    # Fallback parse
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "low_level_keywords" in result:
                return result
        except json.JSONDecodeError:
            pass

    words = [w.strip(".,?!") for w in query.split() if len(w) > 3]
    return {"low_level_keywords": words[:5], "high_level_keywords": []}
