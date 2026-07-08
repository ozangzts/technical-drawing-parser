"""Validation and cleanup for product JSON returned by extractors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .product import empty_product_result


PRODUCT_FIELDS = {
    "source_file",
    "brand_name",
    "product_name",
    "document_name",
    "drawing_number",
    "revision",
    "revision_date",
    "sheet",
    "size",
    "scale",
    "units",
    "dimensions",
    "dimension_tables",
    "tables",
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
ALLOWED_REFINEMENT_CLASSIFICATIONS = {
    "dimension",
    "metadata",
    "note",
    "uncertain",
    "irrelevant",
}
ALLOWED_REFINEMENT_LOCAL_CONTEXTS = {
    "title_block",
    "dimension_callout",
    "dimension_table",
    "general_table",
    "drawing_view",
    "note",
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
    warn_about_filename_like_metadata(result, source_file, warnings)
    for list_field in (
        "dimensions",
        "dimension_tables",
        "tables",
        "tolerances",
        "notes",
        "warnings",
    ):
        if not isinstance(result.get(list_field), list):
            warnings.append(f"`{list_field}` was not a list and was reset.")
            result[list_field] = []
    result["dimensions"] = normalize_dimensions(result["dimensions"], warnings)
    result["dimension_tables"] = normalize_tables(
        result["dimension_tables"],
        warnings,
        field_name="dimension_tables",
        include_type=False,
    )
    result["tables"] = normalize_tables(
        result["tables"],
        warnings,
        field_name="tables",
        include_type=True,
    )

    if warnings:
        result["warnings"].extend(warnings)

    return result, warnings


def parse_ocr_target_refinement_response(
    response_text: str,
    target: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    try:
        parsed = json.loads(extract_json_object(response_text))
    except ValueError as error:
        result = empty_ocr_target_refinement(target)
        warning = f"Refinement response was not valid JSON: {error}"
        result["warnings"].append(warning)
        return result, [warning]

    if not isinstance(parsed, dict):
        result = empty_ocr_target_refinement(target)
        warning = "Refinement response JSON was not an object."
        result["warnings"].append(warning)
        return result, [warning]

    result = empty_ocr_target_refinement(target)
    for field in (
        "target_id",
        "page",
        "classification",
        "is_product_dimension",
        "raw_text",
        "visual_text",
        "ocr_text_supported",
        "local_context",
        "visible_label",
        "dimension",
        "metadata",
        "confidence",
        "warnings",
    ):
        if field in parsed:
            result[field] = parsed[field]

    normalize_ocr_target_refinement(result, warnings)
    if warnings:
        result["warnings"].extend(warnings)
    return result, warnings


def empty_ocr_target_refinement(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_id": target.get("id"),
        "page": target.get("page"),
        "classification": "uncertain",
        "is_product_dimension": None,
        "raw_text": None,
        "visual_text": None,
        "ocr_text_supported": None,
        "local_context": "unknown",
        "visible_label": None,
        "dimension": None,
        "metadata": None,
        "confidence": 0.0,
        "warnings": [],
    }


def normalize_ocr_target_refinement(
    result: dict[str, Any],
    warnings: list[str],
) -> None:
    classification = result.get("classification")
    if not isinstance(classification, str):
        result["classification"] = "uncertain"
        warnings.append("Refinement classification was missing and was set to uncertain.")
    else:
        normalized_classification = classification.strip().lower()
        if normalized_classification not in ALLOWED_REFINEMENT_CLASSIFICATIONS:
            result["classification"] = "uncertain"
            warnings.append(
                f"Refinement classification `{classification}` is not allowed and was set to uncertain."
            )
        else:
            result["classification"] = normalized_classification

    if not isinstance(result.get("warnings"), list):
        result["warnings"] = []
        warnings.append("Refinement warnings were not a list and were reset.")

    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)):
        result["confidence"] = 0.0
        warnings.append("Refinement confidence was missing and was set to 0.0.")

    raw_text = result.get("raw_text")
    result["raw_text"] = normalize_scalar(raw_text)
    result["visual_text"] = normalize_scalar(result.get("visual_text"))
    result["visible_label"] = normalize_scalar(result.get("visible_label"))
    result["local_context"] = normalize_refinement_local_context(
        result.get("local_context"),
        warnings,
    )

    ocr_text_supported = result.get("ocr_text_supported")
    if not isinstance(ocr_text_supported, bool):
        result["ocr_text_supported"] = None

    dimension = result.get("dimension")
    if isinstance(dimension, dict):
        normalized_dimensions = normalize_dimensions([dimension], warnings)
        result["dimension"] = normalized_dimensions[0] if normalized_dimensions else None
    elif dimension is not None:
        result["dimension"] = None
        warnings.append("Refinement dimension was not an object and was reset.")

    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        result["metadata"] = {
            "field": normalize_scalar(metadata.get("field")),
            "value": normalize_scalar(metadata.get("value")),
        }
    elif metadata is not None:
        result["metadata"] = None
        warnings.append("Refinement metadata was not an object and was reset.")


def normalize_refinement_local_context(
    value: Any,
    warnings: list[str],
) -> str:
    if not isinstance(value, str):
        return "unknown"

    normalized = value.strip().lower().replace(" ", "_")
    if normalized not in ALLOWED_REFINEMENT_LOCAL_CONTEXTS:
        warnings.append(
            f"Refinement local_context `{value}` is not allowed and was set to unknown."
        )
        return "unknown"
    return normalized


def normalize_scalars(result: dict[str, Any]) -> None:
    for field in (
        "product_name",
        "brand_name",
        "document_name",
        "drawing_number",
        "revision",
        "revision_date",
        "sheet",
        "size",
        "scale",
    ):
        result[field] = normalize_scalar(result.get(field))
    result.pop("units", None)
    result.pop("dimension_units", None)


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


def warn_about_filename_like_metadata(
    result: dict[str, Any],
    source_file: Path,
    warnings: list[str],
) -> None:
    source_stem = source_file.stem.lower()
    source_name = source_file.name.lower()
    for field in ("product_name", "document_name", "drawing_number"):
        value = result.get(field)
        if not isinstance(value, str):
            continue
        normalized = value.strip().lower()
        if normalized == source_name or normalized == source_stem or "." in normalized:
            warnings.append(
                f"`{field}` may contain a source filename or file extension: `{value}`."
            )


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
        normalized_dimension["unit"] = normalize_unit(normalized_dimension.get("unit"))

        normalized_dimension["type"] = normalize_dimension_type(
            normalized_dimension.get("type"),
            warnings,
            index,
        )
        warn_about_suspicious_dimension_symbols(
            normalized_dimension,
            warnings,
        )
        normalized.append(normalized_dimension)

    return normalized


def normalize_unit(value: Any) -> Any:
    value = normalize_scalar(value)
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower()
    normalized = normalized.replace(".", "")
    normalized = " ".join(normalized.split())
    unit_aliases = {
        "millimeter": "mm",
        "millimeters": "mm",
        "millimetre": "mm",
        "millimetres": "mm",
        "milimeter": "mm",
        "milimeters": "mm",
        "mm": "mm",
        "degree": "deg",
        "degrees": "deg",
        "deg": "deg",
        "°": "deg",
        "inch": "in",
        "inches": "in",
        "in": "in",
        "\"": "in",
        "volt": "V",
        "volts": "V",
        "v": "V",
        "amp": "A",
        "amps": "A",
        "ampere": "A",
        "amperes": "A",
        "a": "A",
        "hz": "Hz",
        "hertz": "Hz",
        "%": "%",
        "percent": "%",
        "percentage": "%",
        "c": "C",
        "°c": "C",
        "celsius": "C",
    }
    return unit_aliases.get(normalized, value)


def normalize_tables(
    tables: list[Any],
    warnings: list[str],
    field_name: str,
    include_type: bool,
) -> list[dict[str, Any]]:
    normalized_tables = []
    for table_index, table in enumerate(tables, start=1):
        if not isinstance(table, dict):
            warnings.append(f"{field_name} item {table_index} was not an object and was skipped.")
            continue

        normalized_table = {
            "title": normalize_scalar(table.get("title")),
            "context": normalize_scalar(table.get("context")),
            "rows": normalize_table_rows(
                table.get("rows"),
                table.get("columns"),
                warnings,
                field_name,
                table_index,
            ),
        }
        if include_type:
            normalized_table = {
                "type": normalize_table_type(table.get("type")),
                **normalized_table,
            }
        normalized_tables.append(normalized_table)

    return normalized_tables


def normalize_table_type(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower().replace(" ", "_")
    allowed = {
        "pinout_table",
        "connection_table",
        "specification_table",
        "notes_table",
        "legend_table",
        "unknown",
    }
    return normalized if normalized in allowed else "unknown"


def normalize_table_rows(
    rows: Any,
    columns: Any,
    warnings: list[str],
    field_name: str,
    table_index: int,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        warnings.append(f"{field_name} item {table_index} rows were not a list and were reset.")
        return []

    normalized_rows = []
    column_labels = [
        normalize_scalar(column)
        for column in columns
        if isinstance(column, str)
    ] if isinstance(columns, list) else []

    for row_index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            warnings.append(
                f"{field_name} item {table_index} row {row_index} was not an object and was skipped."
            )
            continue
        normalized_rows.append(
            {
                "label": normalize_scalar(row.get("label")),
                "cells": normalize_table_cells(
                    row,
                    column_labels,
                    warnings,
                    field_name,
                    table_index,
                    row_index,
                ),
            }
        )

    return normalized_rows


def normalize_table_cells(
    row: dict[str, Any],
    column_labels: list[Any],
    warnings: list[str],
    field_name: str,
    table_index: int,
    row_index: int,
) -> list[dict[str, Any]]:
    cells = row.get("cells")
    if isinstance(cells, list):
        return [
            {
                "column": normalize_scalar(cell.get("column")),
                "value": normalize_scalar(cell.get("value")),
            }
            for cell in cells
            if isinstance(cell, dict)
        ]

    values = row.get("values")
    if isinstance(values, list):
        value_columns = column_labels
        if row.get("label") is not None and len(column_labels) == len(values) + 1:
            value_columns = column_labels[1:]
        return [
            {
                "column": value_columns[index] if index < len(value_columns) else None,
                "value": normalize_scalar(value),
            }
            for index, value in enumerate(values)
        ]

    warnings.append(
        f"{field_name} item {table_index} row {row_index} had no cells or values and was reset."
    )
    return []


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
            f"Suspicious diameter symbol in raw_text: `{raw_text}`."
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
