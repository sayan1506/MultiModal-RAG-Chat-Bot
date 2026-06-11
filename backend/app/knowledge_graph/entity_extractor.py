"""Entity extractor — extracts entities and relationships using Gemma 4 via Ollama."""
from __future__ import annotations

import json
import re

import ollama

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a knowledge graph entity extractor.
Given document text and a page image, extract:
1. Named entities (people, organizations, concepts, technical terms, figures)
2. Relationships between entities

Return ONLY valid JSON — no markdown, no explanation, no code fences:
{
  "entities": [
    {"id": "e1", "label": "Entity Name", "type": "Concept|Entity|Figure|Term"}
  ],
  "relationships": [
    {"source": "e1", "target": "e2", "relation": "DESCRIBES|REFERENCES|CONTAINS|RELATED_TO"}
  ]
}"""

# ---------------------------------------------------------------------------
# Models (primary → fallback)
# ---------------------------------------------------------------------------

MODELS = ["gemma4:e4b", "gemma4:26b"]

# Empty result constant — returned on all failure paths
_EMPTY = {"entities": [], "relationships": []}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_entities(text: str, image_bytes: bytes) -> dict:
    """
    Extract entities and relationships from a document page.

    Args:
        text:        Parsed text content of the page (truncated to 2000 chars).
        image_bytes: Raw PNG bytes of the rendered page image.

    Returns:
        Dict with keys "entities" and "relationships".
        Returns {"entities": [], "relationships": []} on any failure.
    """
    prompt_text = EXTRACTION_PROMPT + f"\n\nPage text:\n{text[:2000]}"
    client = ollama.AsyncClient(host="http://localhost:11434")

    for model in MODELS:
        try:
            response = await client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text,
                        "images": [image_bytes],  # vision: page PNG alongside text
                    }
                ],
                options={"temperature": 0.1},  # low temp for deterministic JSON
            )

            raw: str = response["message"]["content"] or ""

            # Strip markdown fences if model added them
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

            # Attempt full JSON parse
            try:
                result = json.loads(raw)
                # Validate expected keys are present
                if "entities" in result and "relationships" in result:
                    return result
                # Keys missing — try next model
                print(f"[entity_extractor] {model} returned JSON but missing keys, trying next...")
                continue
            except json.JSONDecodeError:
                pass

            # Fallback: try to find a JSON object anywhere in the response
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    if "entities" in result and "relationships" in result:
                        return result
                except json.JSONDecodeError:
                    pass

            print(f"[entity_extractor] {model} returned non-parseable output, trying next...")

        except Exception as e:
            print(f"[entity_extractor] {model} error: {e}, trying next model...")
            continue

    print("[entity_extractor] All models failed, returning empty result.")
    return _EMPTY
