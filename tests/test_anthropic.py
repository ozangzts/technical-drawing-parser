import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.anthropic import (
    extract_text_response,
    media_type_for_image,
)


class AnthropicExtractorTests(unittest.TestCase):
    def test_extract_text_response_joins_text_blocks(self) -> None:
        response = {
            "content": [
                {"type": "text", "text": "first"},
                {"type": "tool_use", "name": "ignored"},
                {"type": "text", "text": "second"},
            ]
        }

        self.assertEqual(extract_text_response(response), "first\nsecond")

    def test_media_type_for_image_uses_supported_types(self) -> None:
        self.assertEqual(media_type_for_image(Path("drawing.jpg")), "image/jpeg")
        self.assertEqual(media_type_for_image(Path("drawing.png")), "image/png")
        self.assertEqual(media_type_for_image(Path("drawing.bmp")), "image/png")


if __name__ == "__main__":
    unittest.main()
