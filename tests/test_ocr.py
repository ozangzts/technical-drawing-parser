import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.ocr import (
    build_comparison_values,
    build_ocr_block,
    build_ocr_candidates,
    build_ocr_target_crops,
    build_target_crop_bbox,
    normalize_ocr_value,
    run_ocr_pages,
    select_ocr_target_candidates,
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

    def test_build_ocr_candidates_matches_quantity_without_symbol(self) -> None:
        raw_ocr_blocks = [
            {
                "id": "page_001_ocr_001",
                "page": 1,
                "text": "(x7) 1,02",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "confidence": 0.9,
            }
        ]
        product_json = {
            "dimensions": [
                {
                    "raw_text": "(x7) #1,02",
                    "value": "1,02",
                    "type": "diameter",
                    "quantity": 7,
                }
            ]
        }

        candidates = build_ocr_candidates(raw_ocr_blocks, product_json)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["full_page_status"], "supported")

    def test_build_comparison_values_keeps_raw_and_looser_match_keys(self) -> None:
        values = build_comparison_values(normalize_ocr_value("(x7) #1,02"))

        self.assertTrue({"(x7)1.02", "1.02"}.issubset(values))

    def test_run_ocr_pages_rejects_unknown_engine(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported OCR engine"):
            run_ocr_pages([], engine_name="paddleocr")

    def test_select_ocr_target_candidates_keeps_only_useful_misses(self) -> None:
        candidates = [
            {
                "ocr_block_id": "page_001_ocr_001",
                "page": 1,
                "text": "3",
                "normalized_text": "3",
                "bbox": {"x": 10, "y": 10, "width": 5, "height": 8},
                "confidence": 0.95,
                "classification": "numeric_candidate",
                "full_page_status": "not_found_in_full_page",
            },
            {
                "ocr_block_id": "page_001_ocr_002",
                "page": 1,
                "text": "1:1.41",
                "normalized_text": "1:1.41",
                "bbox": {"x": 20, "y": 20, "width": 30, "height": 8},
                "confidence": 0.95,
                "classification": "ratio_or_scale_candidate",
                "full_page_status": "not_found_in_full_page",
            },
            {
                "ocr_block_id": "page_001_ocr_003",
                "page": 1,
                "text": "#1,83",
                "normalized_text": "Ã˜1.83",
                "bbox": {"x": 40, "y": 40, "width": 30, "height": 10},
                "confidence": 0.91,
                "classification": "diameter_candidate",
                "full_page_status": "not_found_in_full_page",
            },
            {
                "ocr_block_id": "page_001_ocr_004",
                "page": 1,
                "text": "2,54",
                "normalized_text": "2.54",
                "bbox": {"x": 50, "y": 50, "width": 30, "height": 10},
                "confidence": 0.91,
                "classification": "numeric_candidate",
                "full_page_status": "supported",
            },
            {
                "ocr_block_id": "page_001_ocr_005",
                "page": 1,
                "text": "26.06.2026",
                "normalized_text": "26.06.2026",
                "bbox": {"x": 60, "y": 60, "width": 80, "height": 10},
                "confidence": 0.99,
                "classification": "numeric_candidate",
                "full_page_status": "not_found_in_full_page",
            },
            {
                "ocr_block_id": "page_001_ocr_006",
                "page": 1,
                "text": "1/1",
                "normalized_text": "1/1",
                "bbox": {"x": 70, "y": 70, "width": 30, "height": 10},
                "confidence": 0.99,
                "classification": "numeric_candidate",
                "full_page_status": "not_found_in_full_page",
            },
        ]

        selected = select_ocr_target_candidates(candidates)

        self.assertEqual(
            [candidate["ocr_block_id"] for candidate in selected],
            [
                "page_001_ocr_002",
                "page_001_ocr_003",
                "page_001_ocr_005",
                "page_001_ocr_006",
            ],
        )

    def test_build_target_crop_bbox_pads_and_clamps_to_image(self) -> None:
        crop_bbox = build_target_crop_bbox(
            bbox={"x": 5, "y": 5, "width": 20, "height": 10},
            image_width=500,
            image_height=300,
        )

        self.assertEqual(crop_bbox, {"x": 0, "y": 0, "width": 384, "height": 300})

    def test_build_ocr_target_crops_writes_selected_crop(self) -> None:
        from tempfile import TemporaryDirectory

        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "drawing.png"
            output_dir = root / "targets"
            Image.new("RGB", (800, 600), "white").save(image_path)

            targets = build_ocr_target_crops(
                ocr_candidates=[
                    {
                        "ocr_block_id": "page_001_ocr_001",
                        "page": 1,
                        "text": "#1,83",
                        "normalized_text": "Ã˜1.83",
                        "bbox": {"x": 400, "y": 300, "width": 40, "height": 12},
                        "confidence": 0.92,
                        "classification": "diameter_candidate",
                        "full_page_status": "not_found_in_full_page",
                    }
                ],
                page_images=[
                    {
                        "page": 1,
                        "image_path": image_path,
                        "source_ref": "drawing.png#page=1",
                    }
                ],
                output_dir=output_dir,
                output_slug="drawing",
            )

            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]["type"], "ocr_target_crop")
            self.assertTrue(Path(targets[0]["crop_ref"]).exists())


if __name__ == "__main__":
    unittest.main()
