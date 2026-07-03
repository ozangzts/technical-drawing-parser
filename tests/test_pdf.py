import builtins
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pdf import render_pdf_first_page, render_pdf_pages


class PdfTests(unittest.TestCase):
    def test_render_pdf_pages_writes_each_page(self) -> None:
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF is not installed.")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_path = root / "drawing.pdf"
            output_dir = root / "pages"

            document = fitz.open()
            document.new_page(width=100, height=100)
            document.new_page(width=200, height=100)
            document.save(pdf_path)
            document.close()

            rendered_pages = render_pdf_pages(pdf_path, output_dir, "drawing")

            self.assertEqual(len(rendered_pages), 2)
            self.assertEqual(rendered_pages[0]["page"], 1)
            self.assertEqual(rendered_pages[1]["page"], 2)
            self.assertTrue((output_dir / "drawing_page_001.png").exists())
            self.assertTrue((output_dir / "drawing_page_002.png").exists())

    def test_render_pdf_first_page_reports_missing_pymupdf(self) -> None:
        original_import = builtins.__import__

        def import_without_fitz(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("No module named fitz")
            return original_import(name, *args, **kwargs)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_path = root / "drawing.pdf"
            output_path = root / "page.png"
            pdf_path.write_bytes(b"%PDF-1.7\n")

            with patch("builtins.__import__", side_effect=import_without_fitz):
                with self.assertRaisesRegex(RuntimeError, "requires PyMuPDF"):
                    render_pdf_first_page(pdf_path, output_path)


if __name__ == "__main__":
    unittest.main()
