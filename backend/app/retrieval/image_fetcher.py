"""Image fetcher — reads page PNGs from local storage."""
from __future__ import annotations

from pathlib import Path
from app.config import settings


class ImageFetcher:
    def __init__(self):
        self.base_path = Path(settings.local_image_store)

    async def fetch_pages(
        self, file_id: str, page_numbers: list[int]
    ) -> list[dict]:
        """
        Read PNG files from local disk for the given file_id and page numbers.
        Returns list of dicts with page_number, image_bytes, and image_url (local path).
        """
        results = []
        for page_no in page_numbers:
            file_path = self.base_path / file_id / f"page_{page_no:04d}.png"
            if file_path.exists():
                image_bytes = file_path.read_bytes()
                results.append({
                    "page_number": page_no,
                    "image_bytes": image_bytes,
                    "image_url":   str(file_path),  # local path as URI
                })
            else:
                print(f"Image not found: {file_path}")
        return results