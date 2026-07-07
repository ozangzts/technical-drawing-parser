import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.prompt import (
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


if __name__ == "__main__":
    unittest.main()
