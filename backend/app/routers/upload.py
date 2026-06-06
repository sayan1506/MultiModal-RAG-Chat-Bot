"""Upload router — receives files and triggers background ingestion."""
from __future__ import annotations

import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.ingestion.ingest_pipeline import ingest_document
from app.config import settings

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}


@router.post("/upload")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Accept a file, validate it, and kick off background ingestion."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    file_id = str(uuid.uuid4())

    # Save upload to a temp file the background task can read
    contents = await file.read()
    
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max allowed: {settings.max_upload_mb} MB",
        )
        
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(contents)
    tmp.close()

    background_tasks.add_task(
        ingest_document,
        file_path=tmp.name,
        file_id=file_id,
        filename=file.filename or "unknown",
    )

    return {
        "file_id": file_id,
        "status": "processing",
        "filename": file.filename or "unknown",
    }
