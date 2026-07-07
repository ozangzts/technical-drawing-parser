"""Prompt construction for VLM-based technical drawing extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .product import product_schema_description


def build_vlm_prompt(source_file: Path) -> str:
    return f"""You are extracting visible information from a technical drawing.

Return only valid JSON matching the schema below. Do not include markdown fences or explanations.

Rules:
- Extract only information that is visible in the drawing.
- Do not guess missing or unclear values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in raw_text.
- Use null for missing scalar values.
- Use empty arrays when no values are visible.
- Add warnings for unclear, ambiguous, cropped, or unreadable information.
- If units are stated globally, use that unit for dimensions. If units are not visible, use null.
- Extract title-block sheet information such as 1/1 into sheet when visible.
- Use size for sheet sizes such as A3 or A4. Use scale only for drawing scales such as 1:1, 2:1, or NTS.
- For dimensions, include raw_text, value, unit, type, quantity, label, and context when possible.
- Extract dimension tables when visible. Do not ignore table values that describe product variants, cabinet sizes, ranges, or option-dependent dimensions.
- Put table-derived measurements in dimension_tables with their row and column context instead of flattening them into dimensions when the table context is needed to understand the value.
- Put non-dimensional tables such as pinout, connection, specification, note, or legend tables in tables, not in dimension_tables.
- Do not list single-letter symbolic references such as A, B, C, X, or Y as dimensions unless a numeric value is visible with the reference. If the symbol is defined by a table, keep it as table column text or context.
- Do not include developer metadata, coordinates, OCR blocks, fingerprints, or internal notes.

Source file name:
{source_file.name}

Schema:
{product_schema_description()}
"""


def build_tile_vlm_prompt(source_file: Path, tile: dict[str, Any]) -> str:
    tile_id = tile.get("id", "unknown_tile")
    page = tile.get("page", 1)
    bbox = tile.get("bbox")
    return f"""You are extracting visible information from an overlapping crop of a technical drawing.

Return only valid JSON matching the schema below. Do not include markdown fences or explanations.

Rules:
- This image is a crop, not the full drawing.
- Extract only information that is visible inside this crop.
- Do not guess missing or unclear values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in raw_text.
- Use null for missing scalar values.
- Use empty arrays when no values are visible.
- Add warnings when a dimension, note, leader line, arrow, table cell, or schematic connection appears cropped or incomplete.
- If units are stated globally in this crop, use that unit for dimensions. If units are not visible, use null.
- Extract title-block sheet information such as 1/1 into sheet when visible.
- Use size for sheet sizes such as A3 or A4. Use scale only for drawing scales such as 1:1, 2:1, or NTS.
- For dimensions, include raw_text, value, unit, type, quantity, label, and context when possible.
- Extract visible table-derived measurements into dimension_tables when row or column context is needed.
- Put non-dimensional tables such as pinout, connection, specification, note, or legend tables in tables.
- Do not list single-letter symbolic references as dimensions unless a numeric value is visible with the reference.
- Do not include developer metadata, coordinates, OCR blocks, fingerprints, or internal notes.

Source file name:
{source_file.name}

Crop context:
- tile_id: {tile_id}
- page: {page}
- page_space_bbox: {bbox}

Schema:
{product_schema_description()}
"""


def build_ocr_target_refinement_prompt(
    source_file: Path,
    target: dict[str, Any],
) -> str:
    target_id = target.get("id", "unknown_target")
    page = target.get("page", 1)
    bbox = target.get("bbox")
    ocr_text = target.get("text")
    ocr_bbox = target.get("ocr_bbox")
    return f"""You are reviewing a small OCR-targeted crop from a technical drawing.

Return only valid JSON. Do not include markdown fences or explanations.

Goal:
- Classify what this crop shows.
- If it contains a product dimension, extract that dimension.
- If it shows metadata such as scale, date, sheet number, title block text, or other non-dimension information, classify it as metadata.
- If it is unclear, mark it uncertain.

Rules:
- Use the image content as the source of truth. OCR text is only a hint.
- Do not guess missing or unclear values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in raw_text.
- Do not treat title-block metadata as a product dimension.
- Add warnings for cropped, ambiguous, or unreadable information.
- Do not include coordinates except the provided target ids and page number.

Source file name:
{source_file.name}

Target context:
- target_id: {target_id}
- page: {page}
- page_space_bbox: {bbox}
- ocr_text_hint: {ocr_text}
- ocr_bbox: {ocr_bbox}

Schema:
{{
  "target_id": "{target_id}",
  "page": {page},
  "classification": "dimension | metadata | note | uncertain | irrelevant",
  "is_product_dimension": true,
  "raw_text": null,
  "dimension": {{
    "raw_text": null,
    "value": null,
    "unit": null,
    "type": "linear | diameter | radius | angle | thread | pattern | unknown",
    "quantity": null,
    "label": null,
    "context": null
  }},
  "metadata": {{
    "field": null,
    "value": null
  }},
  "confidence": 0.0,
  "warnings": []
}}
"""
