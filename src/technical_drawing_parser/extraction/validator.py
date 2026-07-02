from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .product import empty_product_result


PRODUCT_FIELDS = {
    "source_file",
    "product_name",
    "document_name",
    "drawing_number",
    "revision",
    "revision_date",
    "scale",
    "units",
    "dimensions",
    "tolerances",
    "notes",
    "warnings",
}


def parse_product_json_response(response_text: str, source_file: Path) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    try:
        parsed = json.loads(extract_json_object(response_text))
    except ValueError as error:
        result = empty_product_result(source_file)
        result["warnings"] = [f"Extractor response was not valid JSON: {error}"]
        return result, result["warnings"]

    if not isinstance(parsed, dict):
        result = empty_product_result(source_file)
        result["warnings"] = ["Extractor response JSON was not an object."]
        return result, result["warnings"]

    result = empty_product_result(source_file)
    for field in PRODUCT_FIELDS:
        if field in parsed:
            result[field] = parsed[field]

    result["source_file"] = source_file.name
    for list_field in ("dimensions", "tolerances", "notes", "warnings"):
        if not isinstance(result.get(list_field), list):
            warnings.append(f"`{list_field}` was not a list and was reset.")
            result[list_field] = []

    if warnings:
        result["warnings"].extend(warnings)

    return result, warnings


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = strip_markdown_fence(stripped)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found.")
    return stripped[start : end + 1]


def strip_markdown_fence(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

