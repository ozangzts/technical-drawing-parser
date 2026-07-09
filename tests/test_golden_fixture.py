"""End-to-end regression test: raw model response -> validated, compact product JSON.

This locks in the full pipeline behavior in one place (parsing, table
label/column normalization, and compact formatting together) instead of only
exercising each piece in isolation. If any of them changes how this fixture
is handled, this test fails and the diff shows exactly what changed.

tests/fixtures/sample_raw_response.json is a hand-written stand-in for what a
VLM extractor's raw_response.txt would contain. tests/fixtures/expected_product.json
is the exact text that should be written to outputs/products/*.json for it.
Regenerate the expected file deliberately (not by hand) if a normalization or
formatting change is intended:

    python -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
from technical_drawing_parser.extraction.validator import parse_product_json_response
from technical_drawing_parser.json_format import format_json_compact
raw = Path('tests/fixtures/sample_raw_response.json').read_text(encoding='utf-8')
result, _ = parse_product_json_response(raw, Path('acme_widget42.pdf'))
Path('tests/fixtures/expected_product.json').write_text(format_json_compact(result), encoding='utf-8')
"

Then re-review the diff before committing it.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.validator import parse_product_json_response
from technical_drawing_parser.json_format import format_json_compact

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class GoldenFixtureTests(unittest.TestCase):
    def test_sample_response_produces_expected_compact_product_json(self) -> None:
        raw_response = (FIXTURES_DIR / "sample_raw_response.json").read_text(encoding="utf-8")
        expected_text = (FIXTURES_DIR / "expected_product.json").read_text(encoding="utf-8")

        result, warnings = parse_product_json_response(raw_response, Path("acme_widget42.pdf"))
        rendered = format_json_compact(result)

        self.assertEqual(rendered, expected_text)

        # Also assert on structure directly so an intentional formatting-only
        # change to json_format.py doesn't require re-deriving these checks
        # from a diff against expected_product.json.
        self.assertEqual(
            warnings,
            ["`document_name` may contain a source filename or file extension: `ACME_WIDGET42_Technical_Drawing.pdf`."],
        )

        pinout_table, spec_table, irregular_table = result["tables"]

        self.assertEqual(pinout_table["columns"], ["Pin", "Signal"])
        self.assertEqual(pinout_table["rows"], [["1", "VCC"], ["2", "GND"]])

        self.assertEqual(spec_table["columns"], ["Parameter", "Value"])
        self.assertEqual(
            spec_table["rows"],
            [
                {"label": "1.1 Material", "values": ["Material", "Aluminum"]},
                {"label": "1.2 Finish", "values": ["Finish", "Anodized"]},
            ],
        )

        self.assertNotIn("columns", irregular_table)
        self.assertEqual(
            irregular_table["rows"],
            [
                {"label": None, "cells": [{"column": "A", "value": "1"}]},
                {
                    "label": None,
                    "cells": [{"column": "B", "value": "2"}, {"column": "C", "value": "3"}],
                },
            ],
        )

        self.assertEqual(json.loads(rendered), result)


if __name__ == "__main__":
    unittest.main()
