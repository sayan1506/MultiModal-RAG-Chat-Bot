import os
import json
import base64
import asyncio
import tempfile
from pathlib import Path

from app.ingestion.parser import parse_file
from app.ingestion.renderer import render_pdf_pages, render_pptx_pages
from app.ingestion.gemini_embedder import embed_text_and_image, embed_text
from app.ingestion.pinecone_upserter import upsert_vector

# Shared handoff store for Dev B (knowledge graph pipeline).
# Key: file_id  →  Value: {"pages": [...], "rendered": [...]}
# Replace with a proper queue/Redis in production.
HANDOFF_STORE: dict = {}


def ingest_document(file_path: str, file_id: str, filename: str) -> None:
    try:
        ext = Path(file_path).suffix.lower()

        # ── Parse ────────────────────────────────────────────────
        pages = parse_file(file_path)

        # ── Render ───────────────────────────────────────────────
        if ext == ".pdf":
            rendered = render_pdf_pages(file_path)
        elif ext in (".pptx", ".ppt"):
            rendered = render_pptx_pages(file_path)
        else:
            print(f"No renderer for {ext}, skipping image embedding.")
            rendered = []

        # ── Embed + Upsert ───────────────────────────────────────
        stored_count = 0
        for page in pages:
            text = page.text.strip()
            if not text:
                print(f"Skipping page {page.page_number} (empty text)")
                continue

            # Find matching render (fall back to text-only if no image)
            render = next(
                (r for r in rendered if r.page_number == page.page_number), None
            )

            if render:
                vector = embed_text_and_image(text, render.image_bytes)
            else:
                vector = embed_text(text)

            upsert_vector(
                vector_id=f"{file_id}_{page.page_number}",
                vector=vector,
                metadata={
                    "file_id": file_id,
                    "page": page.page_number,
                    "source": filename,
                    "text": text[:500],
                },
            )
            stored_count += 1
            print(f"Stored page {page.page_number}")

        print(f"Finished. Stored {stored_count} pages for file_id={file_id}")

        # ── Dev B Handoff — trigger KG build ─────────────────────
        parsed_dicts = [
            {
                "page_number": p.page_number,
                "text":        p.text,
                "source_file": p.source_file,
            }
            for p in pages
        ]
        rendered_dicts = [
            {
                "page_number": r.page_number,
                "image_bytes": r.image_bytes,
                "source_file": r.source_file,
            }
            for r in rendered
        ]

        # Keep HANDOFF_STORE for backwards compatibility
        HANDOFF_STORE[file_id] = {
            "filename": filename,
            "pages":    parsed_dicts,
            "rendered": [
                {**d, "image_b64": base64.b64encode(d["image_bytes"]).decode()}
                for d in rendered_dicts
            ],
        }

        # Build the knowledge graph (async builder called from sync context)
        from app.knowledge_graph.mmkg_builder import MMKGBuilder
        builder = MMKGBuilder()
        asyncio.run(
            builder.build(
                file_id=file_id,
                filename=filename,
                parsed_pages=parsed_dicts,
                rendered_pages=rendered_dicts,
            )
        )

    except Exception as e:
        print(f"ingest_document failed for file_id={file_id}: {e}")
        raise