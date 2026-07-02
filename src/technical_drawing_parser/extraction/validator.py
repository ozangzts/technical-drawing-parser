"""Validation and cleanup for product JSON returned by extractors."""

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
    "size",
    "scale",
    "units",
    "dimensions",
    "tolerances",
    "notes",
    "warnings",
}

DIMENSION_FIELDS = [
    "raw_text",
    "value",
    "unit",
    "type",
    "quantity",
    "label",
    "context",
]

ALLOWED_DIMENSION_TYPES = {
    "linear",
    "diameter",
    "radius",
    "angle",
    "thread",
    "pattern",
    "unknown",
}

NULL_STRINGS = {"", "null", "none", "n/a", "na", "-"}
SHEET_SIZES = {"A0", "A1", "A2", "A3", "A4", "A5"}


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
    normalize_scalars(result)
    normalize_size_and_scale(result, warnings)
    for list_field in ("dimensions", "tolerances", "notes", "warnings"):
        if not isinstance(result.get(list_field), list):
            warnings.append(f"`{list_field}` was not a list and was reset.")
            result[list_field] = []
    result["dimensions"] = normalize_dimensions(result["dimensions"], warnings)

    if warnings:
        result["warnings"].extend(warnings)

    return result, warnings


def normalize_scalars(result: dict[str, Any]) -> None:
    for field in (
        "product_name",
        "document_name",
        "drawing_number",
        "revision",
        "revision_date",
        "size",
        "scale",
        "units",
    ):
        result[field] = normalize_scalar(result.get(field))


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        value = repair_text(value).strip()
        if value.lower() in NULL_STRINGS:
            return None
    return value


def normalize_size_and_scale(result: dict[str, Any], warnings: list[str]) -> None:
    size = result.get("size")
    scale = result.get("scale")

    if is_sheet_size(scale) and size is None:
        result["size"] = scale
        result["scale"] = None
        warnings.append("Moved sheet size value from `scale` to `size`.")


def is_sheet_size(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in SHEET_SIZES


def normalize_dimensions(
    dimensions: list[Any],
    warnings: list[str],
) -> list[dict[str, Any]]:
    normalized = []
    for index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            warnings.append(f"Dimension {index} was not an object and was skipped.")
            continue

        normalized_dimension = {field: None for field in DIMENSION_FIELDS}
        for field in DIMENSION_FIELDS:
            if field in dimension:
                normalized_dimension[field] = normalize_scalar(dimension[field])

        normalized_dimension["type"] = normalize_dimension_type(
            normalized_dimension.get("type"),
            warnings,
            index,
        )
        warn_about_suspicious_dimension_symbols(
            normalized_dimension,
            warnings,
            index,
        )
        normalized.append(normalized_dimension)

    return normalized


def normalize_dimension_type(
    value: Any,
    warnings: list[str],
    index: int,
) -> str:
    if not isinstance(value, str):
        return "unknown"

    dimension_type = value.strip().lower().replace(" ", "_")
    type_aliases = {
        "hole_diameter": "diameter",
        "pad_diameter": "diameter",
        "dia": "diameter",
        "diam": "diameter",
        "pitch": "pattern",
    }
    dimension_type = type_aliases.get(dimension_type, dimension_type)

    if dimension_type not in ALLOWED_DIMENSION_TYPES:
        warnings.append(
            f"Dimension {index} type `{value}` is not allowed and was set to unknown."
        )
        return "unknown"

    return dimension_type


def repair_text(value: str) -> str:
    return value.replace("Ã˜", "Ø")


def warn_about_suspicious_dimension_symbols(
    dimension: dict[str, Any],
    warnings: list[str],
    index: int,
) -> None:
    raw_text = dimension.get("raw_text")
    label = dimension.get("label")
    context = dimension.get("context")
    text_context = " ".join(
        value for value in (label, context) if isinstance(value, str)
    ).lower()

    if (
        isinstance(raw_text, str)
        and "#" in raw_text
        and (
            dimension.get("type") == "diameter"
            or "diameter" in text_context
        )
    ):
        warnings.append(
            f"Dimension {index} may contain a misread diameter symbol in raw_text."
        )


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
