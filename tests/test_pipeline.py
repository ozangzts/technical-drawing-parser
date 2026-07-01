import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pipeline import process_inputs


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

            result_path = outputs / "products" / "example_drawing.json"
            self.assertTrue(result_path.exists())
            self.assertEqual(first_summary["processed"], 1)
            self.assertEqual(second_summary["skipped"], 1)

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["document"]["original_filename"], drawing.name)


if __name__ == "__main__":
    unittest.main()
