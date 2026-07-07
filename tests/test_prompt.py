import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.prompt import (
    build_ocr_target_refinement_prompt,
    build_tile_vlm_prompt,
    build_vlm_prompt,
)


class PromptTests(unittest.TestCase):
    def test_prompts_warn_against_symbolic_reference_dimensions(self) -> None:
        source_file = Path("drawing.pdf")

        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("single-letter symbolic references", full_page_prompt)
        self.assertIn("single-letter symbolic references", tile_prompt)

    def test_prompts_preserve_visible_metadata_values(self) -> None:
        source_file = Path("drawing.pdf")

        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("Preserve visible title-block values exactly", full_page_prompt)
        self.assertIn("Preserve visible title-block values exactly", tile_prompt)
        self.assertIn("Do not assign isolated numbers", full_page_prompt)
        self.assertIn("Do not assign isolated numbers", tile_prompt)

    def test_ocr_target_prompt_requires_visual_text_verification(self) -> None:
        prompt = build_ocr_target_refinement_prompt(
            Path("drawing.pdf"),
            {
                "id": "page_001_ocr_target_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
                "text": "13:100",
                "ocr_bbox": {"x": 10, "y": 10, "width": 50, "height": 12},
            },
        )

        self.assertIn("OCR text is only a hint", prompt)
        self.assertIn("visual_text", prompt)
        self.assertIn("ocr_text_supported", prompt)
        self.assertIn("do not use the OCR hint", prompt)
        self.assertIn("Set is_product_dimension to true only", prompt)


if __name__ == "__main__":
    unittest.main()
