import os
import json
import tempfile
from pathlib import Path

from app.ingestion.parser import parse_file
from app.ingestion.renderer import render_pdf_pages, render_pptx_pages
from app.ingestion.gemini_embedder import embed_text_and_image
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
                from app.ingestion.gemini_embedder import embed_text
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
    
        # ── Dev B Handoff ────────────────────────────────────────
        # Serialise rendered images as base64 so Dev B can read from HANDOFF_STORE
        import base64
        HANDOFF_STORE[file_id] = {
            "filename": filename,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "source_file": p.source_file,
                }
                for p in pages
            ],
            "rendered": [
                {
                    "page_number": r.page_number,
                    "image_b64": base64.b64encode(r.image_bytes).decode("utf-8"),
                    "source_file": r.source_file,
                }
                for r in rendered
            ],
        }
        print(f"Handoff ready for Dev B: file_id={file_id}")
    finally:
        # Clean up the temporary file created by the upload router
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Cleanup error: Failed to remove temporary file {file_path}: {e}")