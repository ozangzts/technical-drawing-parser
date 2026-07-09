import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.validator import (
    parse_ocr_target_refinement_response,
    parse_product_json_response,
)


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
  "brand_name": " ACME ",
  "revision": "null",
  "sheet": " 1/1 ",
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
        self.assertEqual(result["brand_name"], "ACME")
        self.assertIsNone(result["revision"])
        self.assertEqual(result["sheet"], "1/1")
        self.assertEqual(result["size"], "A3")
        self.assertIsNone(result["scale"])
        self.assertEqual(result["dimensions"][0]["value"], "1,22")
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

    def test_parse_product_json_response_drops_product_units_without_changing_values(self) -> None:
        response = """{
  "units": "millimetres",
  "dimensions": [
    {
      "raw_text": "44,12",
      "value": "44,12",
      "unit": "millimeters",
      "type": "linear"
    },
    {
      "raw_text": "90°",
      "value": "90",
      "unit": "degrees",
      "type": "angle"
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertNotIn("units", result)
        self.assertNotIn("dimension_units", result)
        self.assertEqual(result["dimensions"][0]["raw_text"], "44,12")
        self.assertEqual(result["dimensions"][0]["value"], "44,12")
        self.assertEqual(result["dimensions"][0]["unit"], "mm")
        self.assertEqual(result["dimensions"][1]["unit"], "deg")

    def test_parse_product_json_response_warns_about_filename_like_metadata(self) -> None:
        response = """{
  "product_name": "DEICO_DE8133_Technical_Drawing.pdf",
  "document_name": "DEICO_DE8133_Technical_Drawing",
  "drawing_number": "DEICO_DE8133_Technical_Drawing.pdf",
  "dimensions": [],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(
            response,
            Path("DEICO_DE8133_Technical_Drawing.pdf"),
        )

        self.assertEqual(
            result["product_name"],
            "DEICO_DE8133_Technical_Drawing.pdf",
        )
        self.assertTrue(any("product_name" in warning for warning in warnings))
        self.assertTrue(any("document_name" in warning for warning in warnings))
        self.assertTrue(any("drawing_number" in warning for warning in warnings))

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
            any(
                "Suspicious diameter symbol in raw_text: `(x7) #1,83 (PAD DIAMETER)`."
                in warning
                for warning in warnings
            )
        )

    def test_parse_product_json_response_preserves_dimension_tables(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [
    {
      "title": "Cabinet sizes",
      "context": "visible table",
      "columns": ["Width", "Depth"],
      "rows": [
        {
          "label": "Single",
          "values": ["600", "800"]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(result["dimension_tables"][0]["title"], "Cabinet sizes")
        self.assertEqual(
            result["dimension_tables"][0]["rows"][0]["cells"],
            [
                {"column": "Width", "value": "600"},
                {"column": "Depth", "value": "800"},
            ],
        )

    def test_parse_product_json_response_preserves_general_tables(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "pinout_table",
      "title": "Connector pinout",
      "context": "visible table",
      "columns": ["Pin", "Signal"],
      "rows": [
        {
          "label": "Pin 1",
          "values": ["GND"]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(result["tables"][0]["type"], "pinout_table")
        self.assertEqual(
            result["tables"][0]["rows"][0]["cells"],
            [{"column": "Signal", "value": "GND"}],
        )

    def test_parse_product_json_response_accepts_legend_table_type(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "legend_table",
      "title": "Symbol legend",
      "context": "visible table",
      "rows": [
        {
          "label": null,
          "cells": [
            {"column": "Symbol", "value": "\\u00d8"},
            {"column": "Meaning", "value": "Diameter"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(result["tables"][0]["type"], "legend_table")

    def test_parse_product_json_response_drops_label_redundant_with_first_cell(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "pinout_table",
      "title": "Connector pinout",
      "context": "visible table",
      "rows": [
        {
          "label": "Pin 1",
          "cells": [
            {"column": "Pin Number", "value": "1"},
            {"column": "Connection", "value": "Analog In #1"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertIsNone(result["tables"][0]["rows"][0]["label"])
        self.assertEqual(
            result["tables"][0]["rows"][0]["cells"],
            [
                {"column": "Pin Number", "value": "1"},
                {"column": "Connection", "value": "Analog In #1"},
            ],
        )

    def test_parse_product_json_response_keeps_label_with_extra_information(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "specification_table",
      "title": "Environmental specifications",
      "context": "visible table",
      "rows": [
        {
          "label": "2.1 Storage Temperature",
          "cells": [
            {"column": "Parameter", "value": "Storage Temperature"},
            {"column": "Value", "value": "-40C to 71C"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(
            result["tables"][0]["rows"][0]["label"],
            "2.1 Storage Temperature",
        )

    def test_parse_product_json_response_keeps_numbered_label_matching_single_word_value(
        self,
    ) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "specification_table",
      "title": "Environmental specifications",
      "context": "visible table",
      "rows": [
        {
          "label": "2.7 Shock",
          "cells": [
            {"column": "Parameter", "value": "Shock"},
            {"column": "Value", "value": "30 G peak"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(result["tables"][0]["rows"][0]["label"], "2.7 Shock")

    def test_parse_product_json_response_collapses_uniform_columns_with_no_labels(
        self,
    ) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "pinout_table",
      "title": "Connector pinout",
      "context": "visible table",
      "rows": [
        {
          "label": "Pin 1",
          "cells": [
            {"column": "Pin Number", "value": "1"},
            {"column": "Connection", "value": "Analog In #1"}
          ]
        },
        {
          "label": "Pin 2",
          "cells": [
            {"column": "Pin Number", "value": "2"},
            {"column": "Connection", "value": "Analog In #3"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        table = result["tables"][0]
        self.assertEqual(table["columns"], ["Pin Number", "Connection"])
        self.assertEqual(
            table["rows"],
            [["1", "Analog In #1"], ["2", "Analog In #3"]],
        )

    def test_parse_product_json_response_collapses_uniform_columns_keeping_real_labels(
        self,
    ) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "specification_table",
      "title": "Environmental specifications",
      "context": "visible table",
      "rows": [
        {
          "label": "2.1 Storage Temperature",
          "cells": [
            {"column": "Parameter", "value": "Storage Temperature"},
            {"column": "Value", "value": "-40C to 71C"}
          ]
        },
        {
          "label": "2.7 Shock",
          "cells": [
            {"column": "Parameter", "value": "Shock"},
            {"column": "Value", "value": "30 G peak"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        table = result["tables"][0]
        self.assertEqual(table["columns"], ["Parameter", "Value"])
        self.assertEqual(
            table["rows"],
            [
                {"label": "2.1 Storage Temperature", "values": ["Storage Temperature", "-40C to 71C"]},
                {"label": "2.7 Shock", "values": ["Shock", "30 G peak"]},
            ],
        )

    def test_parse_product_json_response_keeps_cells_when_columns_are_not_uniform(
        self,
    ) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [
    {
      "type": "unknown",
      "title": "Irregular table",
      "context": "visible table",
      "rows": [
        {
          "label": null,
          "cells": [
            {"column": "Pin", "value": "1"},
            {"column": "Connection", "value": "GND"}
          ]
        },
        {
          "label": null,
          "cells": [
            {"column": "Signal", "value": "CANH"}
          ]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        table = result["tables"][0]
        self.assertNotIn("columns", table)
        self.assertEqual(
            table["rows"],
            [
                {
                    "label": None,
                    "cells": [
                        {"column": "Pin", "value": "1"},
                        {"column": "Connection", "value": "GND"},
                    ],
                },
                {
                    "label": None,
                    "cells": [{"column": "Signal", "value": "CANH"}],
                },
            ],
        )

    def test_parse_product_json_response_normalizes_schematics(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [],
  "schematics": [
    {
      "title": "Stub Termination Network",
      "context": "BUS to BUS with 3 stub taps, each through a transformer",
      "components": ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"],
      "parameters": [
        {"label": "transformer turns ratio", "value": "1:1,41", "context": "each stub tap"}
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(
            result["schematics"],
            [
                {
                    "title": "Stub Termination Network",
                    "context": "BUS to BUS with 3 stub taps, each through a transformer",
                    "components": ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"],
                    "parameters": [
                        {
                            "label": "transformer turns ratio",
                            "value": "1:1,41",
                            "context": "each stub tap",
                        }
                    ],
                }
            ],
        )

    def test_parse_product_json_response_defaults_schematics_to_empty(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(warnings, [])
        self.assertEqual(result["schematics"], [])

    def test_parse_product_json_response_skips_invalid_schematic_entries(self) -> None:
        response = """{
  "dimensions": [],
  "dimension_tables": [],
  "tables": [],
  "schematics": [
    "not an object",
    {
      "title": "Valid Entry",
      "context": null,
      "components": ["R1", 5, null],
      "parameters": "not a list"
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""

        result, warnings = parse_product_json_response(response, Path("drawing.jpg"))

        self.assertEqual(len(warnings), 2)
        self.assertIn("schematics item 1 was not an object", warnings[0])
        self.assertIn("schematics item 2 parameters was not a list", warnings[1])
        self.assertEqual(len(result["schematics"]), 1)
        self.assertEqual(result["schematics"][0]["title"], "Valid Entry")
        self.assertEqual(result["schematics"][0]["components"], ["R1"])
        self.assertEqual(result["schematics"][0]["parameters"], [])

    def test_parse_ocr_target_refinement_preserves_visual_text_check(self) -> None:
        response = """{
  "target_id": "page_001_ocr_target_001",
  "page": 1,
  "classification": "metadata",
  "is_product_dimension": false,
  "raw_text": "12:100",
  "visual_text": "12:100",
  "ocr_text_supported": false,
  "local_context": "title_block",
  "visible_label": "SCALE",
  "dimension": null,
  "metadata": {
    "field": "scale",
    "value": "12:100"
  },
  "confidence": 0.92,
  "warnings": []
}"""

        result, warnings = parse_ocr_target_refinement_response(
            response,
            {"id": "page_001_ocr_target_001", "page": 1},
        )

        self.assertEqual(warnings, [])
        self.assertEqual(result["visual_text"], "12:100")
        self.assertIs(result["ocr_text_supported"], False)
        self.assertEqual(result["local_context"], "title_block")
        self.assertEqual(result["visible_label"], "SCALE")
        self.assertEqual(result["metadata"]["value"], "12:100")


if __name__ == "__main__":
    unittest.main()
