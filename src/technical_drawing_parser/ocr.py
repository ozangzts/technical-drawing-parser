"""Optional OCR helpers for page images."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image


OCR_CANDIDATE_PATTERN = re.compile(
    r"(?i)(?:\(?x\d+\)?\s*)?(?:[øØ#]\s*)?\d+(?:[,.]\d+)?(?::\d+(?:[,.]\d+)?)?"
)


DEFAULT_OCR_ENGINE = "rapidocr"
SUPPORTED_OCR_ENGINES = {DEFAULT_OCR_ENGINE}
WEAK_SINGLE_NUMBER_PATTERN = re.compile(r"^\d$")
QUANTITY_PREFIX_PATTERN = re.compile(r"(?i)^\(?x\d+\)?")
DIAMETER_SYMBOL_PATTERN = re.compile(r"[øØ#]")
DEFAULT_OCR_TARGET_MIN_CONFIDENCE = 0.75
DEFAULT_OCR_TARGET_PADDING_PX = 160
DEFAULT_OCR_TARGET_MIN_SIZE_PX = 384
DEFAULT_OCR_TARGET_MAX_SIZE_PX = 1024


def run_ocr_pages(
    page_images: list[dict[str, object]],
    engine_name: str = DEFAULT_OCR_ENGINE,
) -> list[dict[str, Any]]:
    if engine_name != DEFAULT_OCR_ENGINE:
        raise ValueError(f"Unsupported OCR engine: {engine_name}")
    return run_rapidocr_pages(page_images)


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
        comparable_values = build_comparison_values(normalized_text)
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
                if comparable_values.intersection(full_page_values)
                else "not_found_in_full_page",
            }
        )
    return candidates


def build_ocr_target_crops(
    ocr_candidates: list[dict[str, Any]],
    page_images: list[dict[str, object]],
    output_dir: Path,
    output_slug: str,
    min_confidence: float = DEFAULT_OCR_TARGET_MIN_CONFIDENCE,
    padding_px: int = DEFAULT_OCR_TARGET_PADDING_PX,
    min_size_px: int = DEFAULT_OCR_TARGET_MIN_SIZE_PX,
    max_size_px: int = DEFAULT_OCR_TARGET_MAX_SIZE_PX,
) -> list[dict[str, Any]]:
    selected_candidates = select_ocr_target_candidates(
        ocr_candidates,
        min_confidence=min_confidence,
    )
    images_by_page = {
        int(page_image.get("page", 1)): page_image for page_image in page_images
    }
    targets: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, candidate in enumerate(selected_candidates, start=1):
        page = candidate.get("page")
        bbox = candidate.get("bbox")
        if not isinstance(page, int) or not isinstance(bbox, dict):
            continue

        page_image = images_by_page.get(page)
        if not page_image:
            continue

        image_path = Path(str(page_image["image_path"]))
        with Image.open(image_path) as image:
            crop_bbox = build_target_crop_bbox(
                bbox=bbox,
                image_width=image.width,
                image_height=image.height,
                padding_px=padding_px,
                min_size_px=min_size_px,
                max_size_px=max_size_px,
            )
            if crop_bbox is None:
                continue

            left = crop_bbox["x"]
            top = crop_bbox["y"]
            right = left + crop_bbox["width"]
            bottom = top + crop_bbox["height"]
            target_id = f"page_{page:03d}_ocr_target_{index:03d}"
            crop_path = output_dir / f"{output_slug}_{target_id}.png"
            image.crop((left, top, right, bottom)).save(crop_path)

        targets.append(
            {
                "id": target_id,
                "type": "ocr_target_crop",
                "page": page,
                "bbox": crop_bbox,
                "ocr_bbox": bbox,
                "source_ocr_block_id": candidate.get("ocr_block_id"),
                "text": candidate.get("text"),
                "normalized_text": candidate.get("normalized_text"),
                "classification": candidate.get("classification"),
                "full_page_status": candidate.get("full_page_status"),
                "source_ref": page_image.get("source_ref"),
                "crop_ref": str(crop_path),
                "confidence": candidate.get("confidence"),
                "padding_px": padding_px,
                "selection_reason": (
                    "High-confidence OCR numeric candidate was not found in the "
                    "full-page extraction."
                ),
            }
        )

    return targets


def select_ocr_target_candidates(
    ocr_candidates: list[dict[str, Any]],
    min_confidence: float = DEFAULT_OCR_TARGET_MIN_CONFIDENCE,
) -> list[dict[str, Any]]:
    selected = []
    for candidate in ocr_candidates:
        if candidate.get("full_page_status") != "not_found_in_full_page":
            continue

        confidence = candidate.get("confidence")
        if not isinstance(confidence, (int, float)) or confidence < min_confidence:
            continue

        normalized_text = candidate.get("normalized_text")
        classification = candidate.get("classification")
        if not isinstance(normalized_text, str) or not isinstance(classification, str):
            continue
        if is_weak_ocr_target(normalized_text, classification):
            continue

        selected.append(candidate)
    return selected


def is_weak_ocr_target(normalized_text: str, classification: str) -> bool:
    if WEAK_SINGLE_NUMBER_PATTERN.fullmatch(normalized_text):
        return True
    return False


def build_target_crop_bbox(
    bbox: dict[str, Any],
    image_width: int,
    image_height: int,
    padding_px: int = DEFAULT_OCR_TARGET_PADDING_PX,
    min_size_px: int = DEFAULT_OCR_TARGET_MIN_SIZE_PX,
    max_size_px: int = DEFAULT_OCR_TARGET_MAX_SIZE_PX,
) -> dict[str, int] | None:
    required_fields = ("x", "y", "width", "height")
    if any(field not in bbox for field in required_fields):
        return None

    x = int(bbox["x"])
    y = int(bbox["y"])
    width = int(bbox["width"])
    height = int(bbox["height"])
    if width <= 0 or height <= 0:
        return None

    target_width = max(width + padding_px * 2, min_size_px)
    target_height = max(height + padding_px * 2, min_size_px)
    target_width = min(target_width, max_size_px, image_width)
    target_height = min(target_height, max_size_px, image_height)

    center_x = x + width / 2
    center_y = y + height / 2
    left = round(center_x - target_width / 2)
    top = round(center_y - target_height / 2)
    left = clamp(left, 0, max(0, image_width - target_width))
    top = clamp(top, 0, max(0, image_height - target_height))

    return {
        "x": int(left),
        "y": int(top),
        "width": int(target_width),
        "height": int(target_height),
    }


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


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
                values.update(build_comparison_values(normalize_ocr_value(str(value))))
    return values


def build_comparison_values(normalized_text: str) -> set[str]:
    values = {normalized_text}
    without_diameter = DIAMETER_SYMBOL_PATTERN.sub("", normalized_text)
    without_quantity = QUANTITY_PREFIX_PATTERN.sub("", normalized_text)
    without_both = QUANTITY_PREFIX_PATTERN.sub("", without_diameter)
    values.update(
        value
        for value in (without_diameter, without_quantity, without_both)
        if value
    )
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
