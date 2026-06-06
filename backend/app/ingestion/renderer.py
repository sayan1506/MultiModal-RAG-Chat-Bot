import fitz
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RenderedPage:
    page_number: int
    image_bytes: bytes
    source_file: str


def render_pdf_pages(file_path: str, dpi: int = 150):
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