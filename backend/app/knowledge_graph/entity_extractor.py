"""Entity extractor — extracts entities and relationships using GPT-4o-mini.

Uses the exact prompt structure from the MegaRAG paper (Figure 2):
- Chain-of-thought reasoning steps
- Rich entity types matching paper's taxonomy
- One-shot exemplar pattern
- Vision: page image + extracted text + layout detection images

Model: GitHub GPT-4o-mini (paper-faithful) → Gemma4 fallback
"""
from __future__ import annotations

import json
import re
import time

from app.ingestion.github_client import call_gpt4o_mini_vision

# ---------------------------------------------------------------------------
# Entity types — from MegaRAG paper Figure 2
# ---------------------------------------------------------------------------
ENTITY_TYPES = [
    "person",
    "organization",
    "job_title",
    "concept_or_framework",
    "quote_or_statement",
    "challenge_or_problem",
    "question_or_use_case",
    "technology_investment_area",
    "business_goal_or_value",
    "audience_or_stakeholder",
    "figure",     # charts, diagrams, images
    "table",      # data tables
]

ENTITY_TYPES_STR = ", ".join(ENTITY_TYPES)

# ---------------------------------------------------------------------------
# Extraction prompt — mirrors MegaRAG paper Figure 2 structure
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a knowledge graph entity extractor for multimodal documents.
Given a document page image and its text content, extract entities and relationships.
Return ONLY valid JSON — no markdown, no explanation, no code fences.
"""

_EXTRACTION_PROMPT_TEMPLATE = """Extract entities and relationships from the document page provided.

Entity types to extract: [{entity_types}]

Instructions:
1. Identify all meaningful entities from the text content AND the page image.
2. For figures (charts, diagrams): treat each as a single "figure" entity with a descriptive name.
3. For tables: treat each as a single "table" entity with a descriptive name.
4. For decorative images or logos: ignore them.
5. For each entity extract: name, type, and a description.
6. Identify relationships between entities with: source, target, description, keywords, strength (1-10).

Page text content:
{text}

Return this exact JSON structure:
{{
  "entities": [
    {{
      "id": "e1",
      "label": "Entity Name",
      "type": "one_of_the_entity_types",
      "description": "Comprehensive description of entity"
    }}
  ],
  "relationships": [
    {{
      "source": "e1",
      "target": "e2",
      "relation": "RELATION_TYPE",
      "description": "Why these are related",
      "keywords": ["keyword1", "keyword2"],
      "strength": 8
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# Empty result constant
# ---------------------------------------------------------------------------
_EMPTY: dict = {"entities": [], "relationships": []}

# Rate limit: 10 RPM = 6 seconds between calls minimum
_RATE_LIMIT_SLEEP = 6.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_entities(text: str, image_bytes: bytes) -> dict:
    """
    Extract entities and relationships from a document page.

    Args:
        text:        Parsed text content of the page (truncated to 3000 chars).
        image_bytes: Raw PNG bytes of the rendered page image.

    Returns:
        Dict with keys "entities" and "relationships".
        Returns {"entities": [], "relationships": []} on any failure.
    """
    prompt = _EXTRACTION_PROMPT_TEMPLATE.format(
        entity_types=ENTITY_TYPES_STR,
        text=text[:3000],
    )

    # Rate limit: sleep between calls to respect 10 RPM
    time.sleep(_RATE_LIMIT_SLEEP)

    raw = call_gpt4o_mini_vision(
        prompt=prompt,
        image_bytes_list=[image_bytes],
        max_tokens=2000,
        temperature=0.0,
    )

    if not raw:
        print("[entity_extractor] Empty response, returning empty result.")
        return _EMPTY

    return _parse_json_response(raw, caller="entity_extractor")


async def extract_entities_with_subgraph(
    text: str,
    image_bytes: bytes,
    subgraph_context: str,
) -> dict:
    """
    Refinement-stage extraction: extracts NEW entities and relationships
    not already present in the provided subgraph context.

    Args:
        text:             Page text content.
        image_bytes:      Page PNG bytes.
        subgraph_context: String representation of the current subgraph
                          (top-120 entities/relations from initial MMKG).

    Returns:
        Dict with NEW entities and relationships to add to the graph.
    """
    prompt = _build_refinement_prompt(text, subgraph_context)

    time.sleep(_RATE_LIMIT_SLEEP)

    raw = call_gpt4o_mini_vision(
        prompt=prompt,
        image_bytes_list=[image_bytes],
        max_tokens=2000,
        temperature=0.0,
    )

    if not raw:
        return _EMPTY

    return _parse_json_response(raw, caller="entity_extractor_refinement")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_refinement_prompt(text: str, subgraph_context: str) -> str:
    """Build the refinement prompt (mirrors MegaRAG paper Figure 3)."""
    # Truncate subgraph to stay within token budget
    subgraph_truncated = subgraph_context[:8000]

    return f"""You are refining a knowledge graph for a multimodal document.

You are given:
1. A document page (image + text)
2. An existing knowledge graph subgraph for this page

Your task: identify ONLY NEW entities and relationships NOT already in the subgraph.
Focus on:
- Entities mentioned in the text that are missing from the subgraph
- Relationships between existing entities suggested by the content but missing
- Cross-modal relationships: connections between text entities and figure/table entities
- Cross-page connections implied by the content

Entity types: [{ENTITY_TYPES_STR}]

Existing Knowledge Graph Subgraph:
{subgraph_truncated}

Page text content:
{text[:3000]}

Return ONLY new entities and relationships in this exact JSON structure:
{{
  "entities": [
    {{
      "id": "new_e1",
      "label": "New Entity Name",
      "type": "entity_type",
      "description": "Description"
    }}
  ],
  "relationships": [
    {{
      "source": "existing_or_new_label",
      "target": "existing_or_new_label",
      "relation": "RELATION_TYPE",
      "description": "Why related",
      "keywords": ["keyword"],
      "strength": 7
    }}
  ]
}}

If nothing new is found, return: {{"entities": [], "relationships": []}}"""


def _parse_json_response(raw: str, caller: str) -> dict:
    """Parse JSON from model response, with fallback regex extraction."""
    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Attempt full parse
    try:
        result = json.loads(raw)
        if "entities" in result and "relationships" in result:
            return result
        print(f"[{caller}] JSON missing required keys.")
    except json.JSONDecodeError:
        pass

    # Fallback: find JSON object anywhere in response
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "entities" in result and "relationships" in result:
                return result
        except json.JSONDecodeError:
            pass

    print(f"[{caller}] Could not parse JSON response.")
    return _EMPTY
