"""PDF rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_PDF_DPI = 200


def render_pdf_first_page(
    pdf_path: Path,
    output_path: Path,
    dpi: int = DEFAULT_PDF_DPI,
) -> dict[str, Any]:
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError(
            "PDF rendering requires PyMuPDF. Install the environment from "
            "environment.yml before processing PDF inputs."
        ) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as document:
        if document.page_count < 1:
            raise ValueError("PDF does not contain any pages.")

        page = document.load_page(0)
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        pixmap.save(output_path)

        page_rect = page.rect
        return {
            "path": str(output_path),
            "page": 1,
            "dpi": dpi,
            "width": int(pixmap.width),
            "height": int(pixmap.height),
            "pdf_width_points": float(page_rect.width),
            "pdf_height_points": float(page_rect.height),
        }
