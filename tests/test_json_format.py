import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.json_format import format_json_compact


class JsonFormatTests(unittest.TestCase):
    def test_round_trips_without_changing_values(self) -> None:
        data = {
            "source_file": "drawing.pdf",
            "brand_name": "DEICO",
            "dimensions": [
                {
                    "raw_text": "482,6",
                    "value": "482,6",
                    "unit": "mm",
                    "type": "linear",
                    "quantity": None,
                    "label": "overall width",
                    "context": "Front view overall width",
                }
            ],
            "tables": [
                {
                    "type": "pinout_table",
                    "title": "Connector pinout",
                    "context": None,
                    "rows": [
                        {
                            "label": None,
                            "cells": [
                                {"column": "Pin Number", "value": "1"},
                                {"column": "Connection", "value": "Analog In #1"},
                            ],
                        }
                    ],
                }
            ],
            "notes": [],
            "warnings": [],
        }

        rendered = format_json_compact(data)

        self.assertEqual(json.loads(rendered), data)

    def test_short_rows_render_on_a_single_line(self) -> None:
        data = {
            "rows": [
                {
                    "label": None,
                    "cells": [
                        {"column": "Pin Number", "value": "1"},
                        {"column": "Connection", "value": "Analog In #1"},
                    ],
                }
            ]
        }

        rendered = format_json_compact(data)
        lines = rendered.splitlines()

        row_lines = [line for line in lines if "Pin Number" in line]
        self.assertEqual(len(row_lines), 1)
        self.assertIn('"cells": [{ "column": "Pin Number", "value": "1" }', row_lines[0])

    def test_long_value_falls_back_to_expanded_form_without_truncation(self) -> None:
        long_value = "A" * 500
        data = {
            "rows": [
                {
                    "label": None,
                    "cells": [
                        {"column": "Parameter", "value": "Notes"},
                        {"column": "Value", "value": long_value},
                    ],
                }
            ]
        }

        rendered = format_json_compact(data)

        self.assertEqual(json.loads(rendered), data)
        value_lines = [line for line in rendered.splitlines() if long_value in line]
        self.assertEqual(len(value_lines), 1)
        self.assertNotIn("Parameter", value_lines[0])

    def test_non_ascii_values_are_preserved_unescaped(self) -> None:
        data = {"notes": ["-40°C to 71°C"]}

        rendered = format_json_compact(data)

        self.assertIn("°C", rendered)
        self.assertEqual(json.loads(rendered), data)


if __name__ == "__main__":
    unittest.main()
