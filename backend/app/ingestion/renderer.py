import fitz
import subprocess
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RenderedPage:
    page_number: int
    image_bytes: bytes
    source_file: str


def render_pdf_pages(file_path: str, dpi: int = 150) -> list[RenderedPage]:
    doc = fitz.open(file_path)
    rendered = []
    for i, page in enumerate(doc):
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        rendered.append(
            RenderedPage(
                page_number=i + 1,
                image_bytes=png_bytes,
                source_file=file_path,
            )
        )
    return rendered


def render_pptx_pages(file_path: str, dpi: int = 150) -> list[RenderedPage]:
    """Convert PPTX → PDF via LibreOffice, then render PDF pages to PNG."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", tmp,
                file_path,
            ],
            check=True,
            capture_output=True,
        )
        pdf_path = os.path.join(tmp, Path(file_path).stem + ".pdf")
        return render_pdf_pages(pdf_path, dpi=dpi)