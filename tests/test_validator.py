import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.validator import parse_product_json_response


class ValidatorTests(unittest.TestCase):
    def test_parse_product_json_response_accepts_markdown_fenced_json(self) -> None:
        response = """```json
{
  "product_name": "Example",
  "dimensions": [],
  "tolerances": [],
  "notes": [],
  "warnings": []
}
```"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(result["source_file"], "drawing.jpg")
        self.assertEqual(result["product_name"], "Example")
        self.assertEqual(warnings, [])

    def test_parse_product_json_response_falls_back_on_invalid_json(self) -> None:
        result, warnings = parse_product_json_response("not json", Path("drawing.jpg"))

        self.assertEqual(result["source_file"], "drawing.jpg")
        self.assertTrue(warnings)
        self.assertIn("Extractor response was not valid JSON", result["warnings"][0])


if __name__ == "__main__":
    unittest.main()
