"""Optional OCR helpers for page images."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


OCR_CANDIDATE_PATTERN = re.compile(
    r"(?i)(?:\(?x\d+\)?\s*)?(?:[øØ#]\s*)?\d+(?:[,.]\d+)?(?::\d+(?:[,.]\d+)?)?"
)


def run_rapidocr_pages(
    page_images: list[dict[str, object]],
) -> list[dict[str, Any]]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise RuntimeError(
            "OCR requires rapidocr-onnxruntime. Install the environment from "
            "environment.yml before using --ocr."
        ) from error

    engine = RapidOCR()
    blocks: list[dict[str, Any]] = []
    for page_image in page_images:
        page = page_image.get("page", 1)
        image_path = Path(str(page_image["image_path"]))
        source_ref = str(page_image["source_ref"])
        result, elapsed = engine(str(image_path))
        for index, item in enumerate(result or [], start=1):
            block = build_ocr_block(
                item=item,
                page=int(page),
                index=index,
                source_ref=source_ref,
                engine="rapidocr-onnxruntime",
                elapsed=elapsed,
            )
            if block:
                blocks.append(block)
    return blocks


def build_ocr_block(
    item: Any,
    page: int,
    index: int,
    source_ref: str,
    engine: str,
    elapsed: Any,
) -> dict[str, Any] | None:
    if not isinstance(item, (list, tuple)) or len(item) < 3:
        return None

    polygon, text, confidence = item[:3]
    bbox = polygon_to_bbox(polygon)
    if bbox is None or not isinstance(text, str):
        return None

    return {
        "id": f"page_{page:03d}_ocr_{index:03d}",
        "page": page,
        "text": text,
        "bbox": bbox,
        "source_ref": source_ref,
        "engine": engine,
        "confidence": float(confidence),
        "elapsed": elapsed,
    }


def polygon_to_bbox(polygon: Any) -> dict[str, int] | None:
    if not isinstance(polygon, (list, tuple)) or not polygon:
        return None

    xs = []
    ys = []
    for point in polygon:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return None
        xs.append(float(point[0]))
        ys.append(float(point[1]))

    min_x = int(min(xs))
    min_y = int(min(ys))
    max_x = int(max(xs))
    max_y = int(max(ys))
    return {
        "x": min_x,
        "y": min_y,
        "width": max(0, max_x - min_x),
        "height": max(0, max_y - min_y),
    }


def build_ocr_candidates(
    raw_ocr_blocks: list[dict[str, Any]],
    full_page_product_json: dict[str, Any],
) -> list[dict[str, Any]]:
    full_page_values = collect_full_page_dimension_values(full_page_product_json)
    candidates = []
    for block in raw_ocr_blocks:
        text = block.get("text")
        if not isinstance(text, str) or not is_numeric_ocr_candidate(text):
            continue

        normalized_text = normalize_ocr_value(text)
        candidates.append(
            {
                "ocr_block_id": block.get("id"),
                "page": block.get("page"),
                "text": text,
                "normalized_text": normalized_text,
                "bbox": block.get("bbox"),
                "confidence": block.get("confidence"),
                "classification": classify_ocr_candidate(text),
                "full_page_status": "supported"
                if normalized_text in full_page_values
                else "not_found_in_full_page",
            }
        )
    return candidates


def collect_full_page_dimension_values(
    full_page_product_json: dict[str, Any],
) -> set[str]:
    values = set()
    dimensions = full_page_product_json.get("dimensions")
    if not isinstance(dimensions, list):
        return values

    for dimension in dimensions:
        if not isinstance(dimension, dict):
            continue
        for field in ("value", "raw_text"):
            value = dimension.get(field)
            if value is not None:
                values.add(normalize_ocr_value(str(value)))
    return values


def is_numeric_ocr_candidate(text: str) -> bool:
    stripped = text.strip()
    letters = re.findall(r"[a-zA-Z]", stripped)
    if any(letter.lower() != "x" for letter in letters):
        return False
    return OCR_CANDIDATE_PATTERN.search(stripped) is not None


def normalize_ocr_value(text: str) -> str:
    normalized = text.strip().lower()
    normalized = normalized.replace("ø", "Ø").replace("#", "Ø")
    normalized = normalized.replace(",", ".")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def classify_ocr_candidate(text: str) -> str:
    normalized = text.strip().lower()
    if ":" in normalized:
        return "ratio_or_scale_candidate"
    if any(symbol in text for symbol in ("Ø", "ø", "#")):
        return "diameter_candidate"
    if re.search(r"(?i)\(?x\d+\)?", text):
        return "quantity_candidate"
    return "numeric_candidate"
