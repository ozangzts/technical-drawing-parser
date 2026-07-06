"""User-facing product JSON defaults and schema description."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def empty_product_result(source_file: Path) -> dict[str, Any]:
    return {
        "source_file": source_file.name,
        "product_name": None,
        "document_name": None,
        "drawing_number": None,
        "revision": None,
        "revision_date": None,
        "size": None,
        "scale": None,
        "units": None,
        "dimensions": [],
        "dimension_tables": [],
        "tolerances": [],
        "notes": [],
        "warnings": [
            "Semantic extraction is not implemented yet."
        ],
    }


def product_schema_description() -> str:
    return """{
  "source_file": "string",
  "product_name": "string or null",
  "document_name": "string or null",
  "drawing_number": "string or null",
  "revision": "string or null",
  "revision_date": "string or null",
  "size": "string or null",
  "scale": "string or null",
  "units": "string or null",
  "dimensions": [
    {
      "raw_text": "string",
      "value": "string or null",
      "unit": "string or null",
      "type": "linear | diameter | radius | angle | thread | pattern | unknown",
      "quantity": "number or null",
      "label": "string or null",
      "context": "string or null"
    }
  ],
  "dimension_tables": [
    {
      "title": "string or null",
      "context": "string or null",
      "columns": ["string"],
      "rows": [
        {
          "label": "string or null",
          "values": ["string"]
        }
      ]
    }
  ],
  "tolerances": [],
  "notes": [],
  "warnings": []
}"""
