"""Upload router — receives multimodal files for future ingestion."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, UploadFile

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_file(file: UploadFile) -> dict[str, str]:
    """Accept a file upload and return a stub acknowledgement.

    In future phases this endpoint will hand the file off to the
    ingestion pipeline for parsing, chunking, and embedding.
    """
    file_id: str = str(uuid.uuid4())
    return {
        "file_id": file_id,
        "status": "received",
        "filename": file.filename or "unknown",
    }
