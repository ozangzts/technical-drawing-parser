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

    def test_parse_product_json_response_normalizes_common_model_output(self) -> None:
        response = """{
  "product_name": " Example ",
  "revision": "null",
  "size": "",
  "scale": "A3",
  "units": "mm",
  "dimensions": [
    {
      "raw_text": "(x11) Ã˜1,22",
      "value": "1,22",
      "unit": "mm",
      "type": "hole diameter",
      "quantity": 11
    },
    {
      "raw_text": "5,08",
      "type": "pitch"
    },
    {
      "raw_text": "unclear",
      "type": "made up"
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(result["product_name"], "Example")
        self.assertIsNone(result["revision"])
        self.assertEqual(result["size"], "A3")
        self.assertIsNone(result["scale"])
        self.assertEqual(result["dimensions"][0]["raw_text"], "(x11) Ø1,22")
        self.assertEqual(result["dimensions"][0]["type"], "diameter")
        self.assertIsNone(result["dimensions"][0]["label"])
        self.assertIsNone(result["dimensions"][0]["context"])
        self.assertEqual(result["dimensions"][1]["type"], "pattern")
        self.assertEqual(result["dimensions"][2]["type"], "unknown")
        self.assertIn("Moved sheet size value from `scale` to `size`.", warnings)
        self.assertTrue(
            any("Dimension 3 type `made up`" in warning for warning in warnings)
        )

    def test_parse_product_json_response_warns_about_suspicious_diameter_symbol(self) -> None:
        response = """{
  "dimensions": [
    {
      "raw_text": "(x7) #1,83 (PAD DIAMETER)",
      "value": "1.83",
      "unit": "mm",
      "type": "diameter",
      "quantity": 7,
      "label": "PAD DIAMETER"
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(
            result["dimensions"][0]["raw_text"],
            "(x7) #1,83 (PAD DIAMETER)",
        )
        self.assertTrue(
            any("misread diameter symbol" in warning for warning in warnings)
        )


if __name__ == "__main__":
    unittest.main()
