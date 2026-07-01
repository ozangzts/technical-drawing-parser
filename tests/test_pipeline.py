import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pipeline import build_output_slug, process_inputs


class PipelineTests(unittest.TestCase):
    def test_process_writes_product_json_and_skips_repeat_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs"
            outputs = root / "outputs"
            inputs.mkdir()
            drawing = inputs / "Example Drawing.jpg"
            drawing.write_bytes(b"\xff\xd8\xff\xd9")

            first_summary = process_inputs(drawing, outputs)
            second_summary = process_inputs(drawing, outputs)

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            prompt_path = outputs / "internal" / "example.vlm_prompt.txt"
            self.assertTrue(result_path.exists())
            self.assertTrue(internal_path.exists())
            self.assertTrue(prompt_path.exists())
            self.assertEqual(first_summary["processed"], 1)
            self.assertEqual(second_summary["skipped"], 1)

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["source_file"], drawing.name)
            self.assertNotIn("fingerprint", result)
            self.assertNotIn("regions", result)
            self.assertIn("Schema:", prompt_path.read_text(encoding="utf-8"))

    def test_build_output_slug_prefers_brand_and_code(self) -> None:
        self.assertEqual(
            build_output_slug("DEICO_DE8135_Technical_Drawing_page-0001"),
            "deico_de8135",
        )


if __name__ == "__main__":
    unittest.main()
