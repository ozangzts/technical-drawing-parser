import builtins
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pdf import render_pdf_first_page


class PdfTests(unittest.TestCase):
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
