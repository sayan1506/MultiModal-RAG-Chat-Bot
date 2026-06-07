"""Entity extractor — uses Gemini to pull entities and relationships from a page."""
from __future__ import annotations

import base64
import json
import re
import time
from google import genai
from google.genai import types
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

EXTRACTION_PROMPT = """You are a knowledge graph entity extractor.
Given document text and a page image, extract:
1. Named entities (people, organizations, concepts, technical terms, figures)
2. Relationships between entities

Return ONLY valid JSON — no markdown, no explanation — in this exact format:
{
  "entities": [
    {"id": "e1", "label": "Entity Name", "type": "Concept|Entity|Figure|Term"}
  ],
  "relationships": [
    {"source": "e1", "target": "e2", "relation": "DESCRIBES|REFERENCES|CONTAINS|RELATED_TO"}
  ]
}"""




async def extract_entities(text: str, image_bytes: bytes) -> dict:
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash-lite"]
    prompt_text = EXTRACTION_PROMPT + f"\n\nPage text:\n{text[:2000]}"

    for model in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        prompt_text,
                    ],
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
                return {"entities": [], "relationships": []}

            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    print(f"{model} unavailable (attempt {attempt+1}), retrying in {2**attempt}s...")
                    time.sleep(2**attempt)
                else:
                    print(f"Entity extraction failed: {e}")
                    return {"entities": [], "relationships": []}

    print("All Gemini models unavailable for entity extraction.")
    return {"entities": [], "relationships": []}