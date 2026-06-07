"""
Image store — saves page PNGs to local disk.
Interface mirrors GCSStore so it can be swapped for real GCS later.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.config import settings


class GCSStore:
    """Local filesystem image store (GCS-compatible interface)."""

    def __init__(self):
        self.base_path = Path(settings.local_image_store)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_page_png(
        self, file_id: str, page_number: int, image_bytes: bytes
    ) -> str:
        """Save PNG to local disk. Returns the file path as the 'URI'."""
        folder = self.base_path / file_id
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"page_{page_number:04d}.png"
        file_path.write_bytes(image_bytes)
        return str(file_path)

    def get_page_urls(
        self, file_id: str, page_numbers: list[int]
    ) -> list[str]:
        """Return local paths for given page numbers."""
        return [
            str(self.base_path / file_id / f"page_{p:04d}.png")
            for p in page_numbers
        ]