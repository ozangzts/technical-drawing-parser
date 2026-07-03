import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.ocr import (
    build_ocr_block,
    build_ocr_candidates,
    normalize_ocr_value,
    run_ocr_pages,
)


class OcrTests(unittest.TestCase):
    def test_build_ocr_block_converts_polygon_to_bbox(self) -> None:
        block = build_ocr_block(
            item=(
                [[10.2, 20.4], [30.9, 20.0], [31.5, 40.8], [9.7, 41.2]],
                "Ø1,83",
                0.91,
            ),
            page=1,
            index=2,
            source_ref="drawing.pdf#page=1",
            engine="test",
            elapsed=[0.1],
        )

        self.assertEqual(block["id"], "page_001_ocr_002")
        self.assertEqual(block["bbox"], {"x": 9, "y": 20, "width": 22, "height": 21})
        self.assertEqual(block["text"], "Ø1,83")

    def test_build_ocr_candidates_marks_full_page_support(self) -> None:
        raw_ocr_blocks = [
            {
                "id": "page_001_ocr_001",
                "page": 1,
                "text": "#1,83",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "confidence": 0.8,
            },
            {
                "id": "page_001_ocr_002",
                "page": 1,
                "text": "ProductName",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "confidence": 0.9,
            },
            {
                "id": "page_001_ocr_003",
                "page": 1,
                "text": "5STUBDTRM|DE8135",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "confidence": 0.9,
            },
        ]
        product_json = {
            "dimensions": [
                {
                    "raw_text": "Ø1,83",
                    "value": "1,83",
                    "type": "diameter",
                }
            ]
        }

        candidates = build_ocr_candidates(raw_ocr_blocks, product_json)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["classification"], "diameter_candidate")
        self.assertEqual(candidates[0]["full_page_status"], "supported")
        self.assertEqual(normalize_ocr_value("#1,83"), "Ø1.83")

    def test_run_ocr_pages_rejects_unknown_engine(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported OCR engine"):
            run_ocr_pages([], engine_name="paddleocr")


if __name__ == "__main__":
    unittest.main()
