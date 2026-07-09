import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.anthropic import (
    extract_text_response,
    media_type_for_image,
    response_was_truncated,
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

    def test_response_was_truncated_detects_max_tokens_stop_reason(self) -> None:
        self.assertTrue(response_was_truncated({"stop_reason": "max_tokens"}))
        self.assertFalse(response_was_truncated({"stop_reason": "end_turn"}))
        self.assertFalse(response_was_truncated({}))
        self.assertFalse(response_was_truncated(None))


if __name__ == "__main__":
    unittest.main()
