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
    rendered_pages = render_pdf_pages(
        pdf_path=pdf_path,
        output_dir=output_path.parent,
        output_slug=output_path.stem.removesuffix("_page_001"),
        dpi=dpi,
    )
    return rendered_pages[0]


def render_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    output_slug: str,
    dpi: int = DEFAULT_PDF_DPI,
) -> list[dict[str, Any]]:
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError(
            "PDF rendering requires PyMuPDF. Install the environment from "
            "environment.yml before processing PDF inputs."
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as document:
        if document.page_count < 1:
            raise ValueError("PDF does not contain any pages.")

        rendered_pages = []
        for page_index in range(document.page_count):
            page_number = page_index + 1
            output_path = output_dir / f"{output_slug}_page_{page_number:03d}.png"
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            pixmap.save(output_path)

            page_rect = page.rect
            rendered_pages.append(
                {
                    "path": str(output_path),
                    "page": page_number,
                    "dpi": dpi,
                    "width": int(pixmap.width),
                    "height": int(pixmap.height),
                    "pdf_width_points": float(page_rect.width),
                    "pdf_height_points": float(page_rect.height),
                }
            )

        return rendered_pages
