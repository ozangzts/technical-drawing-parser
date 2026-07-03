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
- Use size for sheet sizes such as A3 or A4. Use scale only for drawing scales such as 1:1, 2:1, or NTS.
- For dimensions, include raw_text, value, unit, type, quantity, label, and context when possible.
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
- Use size for sheet sizes such as A3 or A4. Use scale only for drawing scales such as 1:1, 2:1, or NTS.
- For dimensions, include raw_text, value, unit, type, quantity, label, and context when possible.
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
