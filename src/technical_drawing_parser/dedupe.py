"""Internal duplicate-candidate summaries for tile extractions."""

from __future__ import annotations

from typing import Any


def build_tile_extraction_summary(
    tile_extractions: list[dict[str, Any]],
    full_page_product_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dimension_candidates = collect_dimension_candidates(tile_extractions)
    duplicate_groups = build_duplicate_candidate_groups(dimension_candidates)
    full_page_candidates = collect_full_page_dimension_candidates(full_page_product_json)
    supported_candidates, tile_only_candidates = classify_full_page_support(
        dimension_candidates,
        full_page_candidates,
    )
    duplicate_ids = {
        candidate["candidate_id"]
        for group in duplicate_groups
        for candidate in group["candidates"]
    }
    unique_candidates = [
        candidate
        for candidate in dimension_candidates
        if candidate["candidate_id"] not in duplicate_ids
    ]

    return {
        "tiles_processed": len(tile_extractions),
        "dimensions_found": len(dimension_candidates),
        "duplicate_candidate_groups": duplicate_groups,
        "full_page_supported_candidates": supported_candidates,
        "tile_only_candidates": tile_only_candidates,
        "unique_dimension_candidates": unique_candidates,
    }


def collect_dimension_candidates(
    tile_extractions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = []
    for tile_extraction in tile_extractions:
        product_json = tile_extraction.get("product_json")
        if not isinstance(product_json, dict):
            continue

        dimensions = product_json.get("dimensions")
        if not isinstance(dimensions, list):
            continue

        for index, dimension in enumerate(dimensions, start=1):
            if not isinstance(dimension, dict):
                continue
            candidate = build_dimension_candidate(tile_extraction, dimension, index)
            if candidate:
                candidates.append(candidate)

    return candidates


def collect_full_page_dimension_candidates(
    full_page_product_json: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(full_page_product_json, dict):
        return []

    dimensions = full_page_product_json.get("dimensions")
    if not isinstance(dimensions, list):
        return []

    candidates = []
    for index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            continue
        candidates.append(
            {
                "candidate_id": f"full_page_dimension_{index:03d}",
                "raw_text": dimension.get("raw_text"),
                "value": dimension.get("value"),
                "type": dimension.get("type"),
                "label": dimension.get("label"),
                "context": dimension.get("context"),
                "quantity": dimension.get("quantity"),
                "dedupe_key": build_dimension_dedupe_key(
                    page=1,
                    dimension=dimension,
                ),
            }
        )
    return candidates


def build_dimension_candidate(
    tile_extraction: dict[str, Any],
    dimension: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    page = tile_extraction.get("page")
    bbox = tile_extraction.get("bbox")
    tile_id = tile_extraction.get("tile_id")
    if not isinstance(page, int) or not isinstance(tile_id, str):
        return None

    raw_text = dimension.get("raw_text")

    return {
        "candidate_id": f"{tile_id}_dimension_{index:03d}",
        "tile_id": tile_id,
        "page": page,
        "bbox": bbox,
        "raw_text": raw_text,
        "value": dimension.get("value"),
        "type": dimension.get("type"),
        "label": dimension.get("label"),
        "context": dimension.get("context"),
        "quantity": dimension.get("quantity"),
        "dedupe_key": build_dimension_dedupe_key(page, dimension),
    }


def build_dimension_dedupe_key(
    page: int,
    dimension: dict[str, Any],
) -> dict[str, Any]:
    return {
        "page": page,
        "value": normalize_value_key(dimension.get("value") or dimension.get("raw_text")),
        "type": normalize_text_key(dimension.get("type")) or "unknown",
        "label": normalize_text_key(dimension.get("label")),
        "quantity": normalize_quantity_key(dimension.get("quantity")),
    }


def build_duplicate_candidate_groups(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = candidate["dedupe_key"]
        group_key = (
            key["page"],
            key["value"],
            key["type"],
            key["label"],
            key["quantity"],
        )
        grouped.setdefault(group_key, []).append(candidate)

    duplicate_groups = []
    for group_candidates in grouped.values():
        if len(group_candidates) < 2:
            continue

        related_candidates = candidates_with_overlapping_tiles(group_candidates)
        if len(related_candidates) < 2:
            continue

        first = related_candidates[0]
        duplicate_groups.append(
            {
                "dedupe_key": first["dedupe_key"],
                "candidate_count": len(related_candidates),
                "reason": "same page/value/type/label with overlapping source tile bboxes",
                "candidates": related_candidates,
            }
        )

    return duplicate_groups


def classify_full_page_support(
    tile_candidates: list[dict[str, Any]],
    full_page_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    supported = []
    tile_only = []
    for candidate in tile_candidates:
        matches = [
            full_page_candidate
            for full_page_candidate in full_page_candidates
            if candidates_match(candidate, full_page_candidate)
        ]
        if matches:
            supported.append(
                {
                    "candidate": candidate,
                    "matching_full_page_candidates": matches,
                    "support_reason": "same page/value/type/label/quantity as full-page extraction",
                }
            )
        else:
            tile_only.append(candidate)

    return supported, tile_only


def candidates_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_key = left.get("dedupe_key")
    right_key = right.get("dedupe_key")
    if not isinstance(left_key, dict) or not isinstance(right_key, dict):
        return False

    required_keys = ("page", "value", "type")
    if any(left_key.get(key) != right_key.get(key) for key in required_keys):
        return False

    for optional_key in ("label", "quantity"):
        left_value = left_key.get(optional_key)
        right_value = right_key.get(optional_key)
        if left_value is not None and right_value is not None and left_value != right_value:
            return False

    return True


def candidates_with_overlapping_tiles(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    related_ids = set()
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            if bboxes_overlap(left.get("bbox"), right.get("bbox")):
                related_ids.add(left["candidate_id"])
                related_ids.add(right["candidate_id"])

    return [
        candidate
        for candidate in candidates
        if candidate["candidate_id"] in related_ids
    ]


def bboxes_overlap(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False

    required_keys = {"x", "y", "width", "height"}
    if not required_keys.issubset(left) or not required_keys.issubset(right):
        return False

    left_x2 = left["x"] + left["width"]
    left_y2 = left["y"] + left["height"]
    right_x2 = right["x"] + right["width"]
    right_y2 = right["y"] + right["height"]

    return not (
        left_x2 <= right["x"]
        or right_x2 <= left["x"]
        or left_y2 <= right["y"]
        or right_y2 <= left["y"]
    )


def normalize_value_key(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower().replace(",", ".")


def normalize_text_key(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().lower().split())
    return normalized or None


def normalize_quantity_key(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().lower() or None
