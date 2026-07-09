import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.ollama import response_was_truncated


class OllamaExtractorTests(unittest.TestCase):
    def test_response_was_truncated_detects_length_done_reason(self) -> None:
        self.assertTrue(response_was_truncated({"done_reason": "length"}))
        self.assertFalse(response_was_truncated({"done_reason": "stop"}))
        self.assertFalse(response_was_truncated({}))
        self.assertFalse(response_was_truncated(None))


if __name__ == "__main__":
    unittest.main()
