"""Gemini embedder — DEPRECATED for embeddings, kept for non-embedding uses.

All embedding calls now route through gme_embedder.py.
This file is kept as a compatibility shim so any existing imports do not break.
"""
from __future__ import annotations

# Re-export GME functions under the old names
from app.ingestion.gme_embedder import (
    embed_text,
    embed_image_bytes as embed_image,
    embed_text_and_image,
)

__all__ = ["embed_text", "embed_image", "embed_text_and_image"]
