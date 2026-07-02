"""Prompt construction for VLM-based technical drawing extraction."""

from __future__ import annotations

from pathlib import Path

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
