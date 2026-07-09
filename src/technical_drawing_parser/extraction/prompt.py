"""Prompt construction for VLM-based technical drawing extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .product import product_schema_description


# Rules below are shared verbatim between the full-page and tile prompts.
# Keeping them as named constants (instead of retyping the same sentence in
# both prompt builders) means a future rule change only has to happen once,
# and the two prompts cannot silently drift apart on wording that was never
# meant to differ.
RULE_NO_GUESSING = "Do not guess missing or unclear values."
RULE_PRESERVE_RAW_TEXT_FORMATTING = (
    "Preserve original numeric formatting, decimal separators, symbols, and "
    "quantity markers in raw_text."
)
RULE_PRESERVE_VALUE_FORMATTING = (
    "Preserve visible numeric formatting in value too. Do not convert decimal "
    "commas to decimal points."
)
RULE_PRESERVE_TITLE_BLOCK_FORMATTING = (
    "Preserve visible title-block values exactly as written, including date "
    "order, separators, revision text, sheet text, and scale ratios."
)
RULE_NULL_FOR_MISSING = "Use null for missing scalar values."
RULE_EMPTY_ARRAYS = "Use empty arrays when no values are visible."
RULE_NO_UNIT_INFERENCE = (
    "Do not infer dimension unit from drawing style, decimal separators, "
    "product type, previous drawings, or common mechanical drawing conventions."
)
RULE_UNIT_SCOPE_EXCLUSIONS = (
    "Do not apply global dimension units to pin numbers, connector labels, "
    "table indexes, dates, scale values, revision values, voltage, current, "
    "temperature, humidity, frequency, standards, or free-text notes unless "
    "that exact value visibly carries that unit."
)
RULE_SHEET_FROM_TITLE_BLOCK = (
    "Extract title-block sheet information such as 1/1 into sheet when visible."
)
RULE_BRAND_VS_PRODUCT_NAME = (
    "Put visible company, manufacturer, brand, or logo text in brand_name, "
    "not product_name."
)
RULE_PRODUCT_NAME_IS_HUMAN_READABLE = (
    "Put human-readable product/model descriptions in product_name. Do not "
    "use brand-only text as product_name."
)
RULE_DRAWING_NUMBER_IS_CONCISE_CODE = (
    "Put the concise visible drawing, part, or model code in drawing_number "
    "when visible."
)
RULE_DRAWING_NUMBER_MAY_BE_EMBEDDED = (
    "A short product or model code, such as DE4001, still belongs in "
    "drawing_number even when it only appears embedded inside the "
    "product_name or document_name text rather than in its own separate "
    "field."
)
RULE_DRAWING_NUMBER_NOT_FORM_STAMP = (
    "Do not use a generic document or form control stamp as drawing_number, "
    "such as a code that carries its own separate revision number and date "
    "printed elsewhere on the sheet (for example SBL-0033 Rev. No:2 Date: "
    "19.12.2025); that identifies the template or form, not this specific "
    "product."
)
RULE_DOCUMENT_NAME_IS_DOCUMENT_TYPE = (
    "Put document type text such as Technical Drawing in document_name."
)
RULE_SOURCE_FILENAME_IS_ONLY_A_HINT = (
    "The source file name is only a processing hint. Do not copy the source "
    "file name into product_name, document_name, or drawing_number unless "
    "that exact text is visibly printed in the drawing."
)
RULE_NO_FULL_FILENAME_AS_DRAWING_NUMBER = (
    "Do not use a full filename such as Brand_Code_Technical_Drawing.pdf as "
    "drawing_number. Prefer the short visible code from the title block, "
    "such as Code1234."
)
RULE_SIZE_VS_SCALE = (
    "Use size for sheet sizes such as A3 or A4. Use scale only for drawing "
    "scales such as 1:1, 2:1, 13:100, or NTS."
)
RULE_NO_ISOLATED_NUMBERS_AS_METADATA = (
    "Do not assign isolated numbers to metadata fields unless a visible "
    "label or title-block context supports the field."
)
RULE_DIMENSION_FIELDS = (
    "For dimensions, include raw_text, value, unit, type, quantity, label, "
    "and context when possible."
)
RULE_DIMENSION_CONTEXT_SPECIFICITY = (
    "Make dimension context specific enough to locate the value, such as "
    "overall width, front view height, connector body radius, or "
    "recommended land pattern hole diameter."
)
RULE_NUMBERED_SPECIFICATION_SECTIONS = (
    "Extract numbered specification sections as tables when they have a "
    "parameter/value structure. Use notes only for free-text notes that do "
    "not form a table."
)
RULE_NO_DEVELOPER_METADATA = (
    "Do not include developer metadata, coordinates, OCR blocks, "
    "fingerprints, or internal notes."
)
RULE_SCHEMATIC_COMPONENTS = (
    "If a schematic or circuit diagram shows component reference "
    "designators, such as R1, C3, or U2, or a named electrical parameter "
    "repeated across the diagram, such as a transformer turns ratio or a "
    "resistor value, extract them into schematics: components as the list "
    "of visible reference designators, and parameters as label/value pairs."
)
RULE_SCHEMATIC_BLOCK_DIAGRAM_FALLBACK = (
    "If a diagram only shows functional blocks and arrows with no "
    "reference designators or values, describe it in warnings instead of "
    "adding an empty or forced schematics entry."
)
RULE_CONSISTENT_ROW_COLUMN_ORDER = (
    "When a table has more than one row, use the same column order in "
    "every row's cells, such as always Pin Number then Connection, so rows "
    "stay aligned with each other."
)


def _rules_block(rules: list[str]) -> str:
    return "\n".join(f"- {rule}" for rule in rules)


def build_vlm_prompt(source_file: Path) -> str:
    rules = _rules_block(
        [
            "Extract only information that is visible in the drawing.",
            RULE_NO_GUESSING,
            RULE_PRESERVE_RAW_TEXT_FORMATTING,
            RULE_PRESERVE_VALUE_FORMATTING,
            RULE_PRESERVE_TITLE_BLOCK_FORMATTING,
            RULE_NULL_FOR_MISSING,
            RULE_EMPTY_ARRAYS,
            "Add warnings for unclear, ambiguous, cropped, or unreadable information.",
            'Use dimension unit only when a unit is visible in a dimension label '
            'or supported by a visible global note such as "all dimensions are '
            'in millimeters".',
            RULE_NO_UNIT_INFERENCE,
            "If dimension units are not visibly stated, use null for dimension unit.",
            'A global note such as "all dimensions are in millimeters" applies '
            "only to physical product dimensions that do not show another unit.",
            RULE_UNIT_SCOPE_EXCLUSIONS,
            RULE_SHEET_FROM_TITLE_BLOCK,
            RULE_BRAND_VS_PRODUCT_NAME,
            RULE_PRODUCT_NAME_IS_HUMAN_READABLE,
            RULE_DRAWING_NUMBER_IS_CONCISE_CODE,
            RULE_DRAWING_NUMBER_MAY_BE_EMBEDDED,
            RULE_DRAWING_NUMBER_NOT_FORM_STAMP,
            RULE_DOCUMENT_NAME_IS_DOCUMENT_TYPE,
            RULE_SOURCE_FILENAME_IS_ONLY_A_HINT,
            RULE_NO_FULL_FILENAME_AS_DRAWING_NUMBER,
            RULE_SIZE_VS_SCALE,
            RULE_NO_ISOLATED_NUMBERS_AS_METADATA,
            RULE_DIMENSION_FIELDS,
            RULE_DIMENSION_CONTEXT_SPECIFICITY,
            "Extract dimension tables when visible. Do not ignore table values "
            "that describe product variants, cabinet sizes, ranges, or "
            "option-dependent dimensions.",
            "Put table-derived measurements in dimension_tables with their row "
            "and column context instead of flattening them into dimensions "
            "when the table context is needed to understand the value.",
            "Put non-dimensional tables such as pinout, connection, "
            "specification, note, or legend tables in tables, not in "
            "dimension_tables.",
            RULE_NUMBERED_SPECIFICATION_SECTIONS,
            "For tables, make rows readable by humans. Use one logical item "
            "per row when possible, such as one pin per row or one "
            "specification per row.",
            "In table rows, use cells as a list of objects with column and "
            "value. Do not put table headers in a separate columns array "
            "with disconnected row values.",
            RULE_CONSISTENT_ROW_COLUMN_ORDER,
            "If the visible table repeats the same headers across multiple "
            "side-by-side blocks, normalize it into logical rows instead of "
            "preserving repeated headers across one very wide row.",
            "Do not list single-letter symbolic references such as A, B, C, "
            "X, or Y as dimensions unless a numeric value is visible with "
            "the reference. If the symbol is defined by a table, keep it as "
            "table column text or context.",
            RULE_SCHEMATIC_COMPONENTS,
            RULE_SCHEMATIC_BLOCK_DIAGRAM_FALLBACK,
            RULE_NO_DEVELOPER_METADATA,
        ]
    )

    return f"""You are extracting visible information from a technical drawing.

Return only valid JSON matching the schema below. Do not include markdown fences or explanations.

Rules:
{rules}

Source file name:
{source_file.name}

Schema:
{product_schema_description()}
"""


def build_tile_vlm_prompt(source_file: Path, tile: dict[str, Any]) -> str:
    tile_id = tile.get("id", "unknown_tile")
    page = tile.get("page", 1)
    bbox = tile.get("bbox")

    rules = _rules_block(
        [
            "This image is a crop, not the full drawing.",
            "Extract only information that is visible inside this crop.",
            RULE_NO_GUESSING,
            RULE_PRESERVE_RAW_TEXT_FORMATTING,
            RULE_PRESERVE_VALUE_FORMATTING,
            RULE_PRESERVE_TITLE_BLOCK_FORMATTING,
            RULE_NULL_FOR_MISSING,
            RULE_EMPTY_ARRAYS,
            "Add warnings when a dimension, note, leader line, arrow, table "
            "cell, or schematic connection appears cropped or incomplete.",
            "Use dimension unit only when a unit is visible in a dimension "
            "label or supported by a visible global note fragment such as "
            '"all dimensions are in millimeters".',
            RULE_NO_UNIT_INFERENCE,
            "If dimension units are not visibly stated in this crop, use "
            "null for dimension unit.",
            'A global note fragment such as "all dimensions are in '
            'millimeters" applies only to physical product dimensions that '
            "do not show another unit.",
            RULE_UNIT_SCOPE_EXCLUSIONS,
            RULE_SHEET_FROM_TITLE_BLOCK,
            RULE_BRAND_VS_PRODUCT_NAME,
            RULE_PRODUCT_NAME_IS_HUMAN_READABLE,
            RULE_DRAWING_NUMBER_IS_CONCISE_CODE,
            RULE_DRAWING_NUMBER_MAY_BE_EMBEDDED,
            RULE_DRAWING_NUMBER_NOT_FORM_STAMP,
            RULE_DOCUMENT_NAME_IS_DOCUMENT_TYPE,
            RULE_SOURCE_FILENAME_IS_ONLY_A_HINT,
            RULE_NO_FULL_FILENAME_AS_DRAWING_NUMBER,
            RULE_SIZE_VS_SCALE,
            RULE_NO_ISOLATED_NUMBERS_AS_METADATA,
            RULE_DIMENSION_FIELDS,
            RULE_DIMENSION_CONTEXT_SPECIFICITY,
            "Extract visible table-derived measurements into dimension_tables "
            "when row or column context is needed.",
            "Put non-dimensional tables such as pinout, connection, "
            "specification, note, or legend tables in tables.",
            RULE_NUMBERED_SPECIFICATION_SECTIONS,
            "For tables, use one logical item per row when possible and "
            "write row cells as objects with column and value.",
            "Do not put table headers in a separate columns array with "
            "disconnected row values.",
            RULE_CONSISTENT_ROW_COLUMN_ORDER,
            "Do not list single-letter symbolic references as dimensions "
            "unless a numeric value is visible with the reference.",
            RULE_SCHEMATIC_COMPONENTS,
            RULE_SCHEMATIC_BLOCK_DIAGRAM_FALLBACK,
            RULE_NO_DEVELOPER_METADATA,
        ]
    )

    return f"""You are extracting visible information from an overlapping crop of a technical drawing.

Return only valid JSON matching the schema below. Do not include markdown fences or explanations.

Rules:
{rules}

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
- Identify the local visual context of the crop, such as title block, dimension callout, table, note, drawing view, or unknown.
- If it contains a product dimension, extract that dimension.
- If it shows metadata such as brand/company text, product name, drawing number, scale, date, sheet number, title block text, or other non-dimension information, classify it as metadata.
- If it is unclear, mark it uncertain.

Rules:
- Use the image content as the source of truth. OCR text is only a hint.
- Re-read the visible text in the crop yourself. Do not copy the OCR hint unless the image supports it.
- If the OCR hint and the visible crop text differ, put the visible crop text in visual_text and set ocr_text_supported to false.
- If ocr_text_supported is false, do not use the OCR hint as the dimension value or metadata value.
- Do not guess missing or unclear values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in raw_text.
- Preserve visible numeric formatting in value too. Do not convert decimal commas to decimal points.
- Preserve visible metadata values exactly as written, including date order, separators, revision text, sheet text, and scale ratios.
- Do not treat title-block metadata as a product dimension.
- Set is_product_dimension to true only for physical product dimensions, not title-block scale, dates, sheet numbers, drawing numbers, notes, or table indexes.
- For metadata, use one of these fields when visible: brand_name, product_name, document_name, drawing_number, revision, revision_date, sheet, size, scale, other.
- Use units only when the unit text is visible in the crop. Do not infer mm, inch, or any other unit from the number format or drawing style.
- Do not apply a global dimension unit to pin numbers, connector labels, table indexes, dates, scale values, revision values, voltage, current, temperature, humidity, frequency, standards, or notes unless that exact visible value carries that unit.
- Use local_context to describe what the crop visually appears to be: title_block, dimension_callout, dimension_table, general_table, drawing_view, note, or unknown.
- Use visible_label for a nearby visible label that supports the classification, such as SCALE, DATE, SHEET, REV, SIZE, UNITS, or a table heading. Use null when no supporting label is visible.
- If the crop contains only an isolated number with no visible label, table structure, leader line, arrow, or title-block context, classify it as uncertain or irrelevant instead of metadata.
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
  "is_product_dimension": null,
  "raw_text": null,
  "visual_text": null,
  "ocr_text_supported": null,
  "local_context": "title_block | dimension_callout | dimension_table | general_table | drawing_view | note | unknown",
  "visible_label": null,
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
    "field": "brand_name | product_name | document_name | drawing_number | revision | revision_date | sheet | size | scale | other | null",
    "value": null
  }},
  "confidence": 0.0,
  "warnings": []
}}
"""
