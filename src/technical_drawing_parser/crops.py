"""Overlapping crop generation for page images."""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_TILE_SIZE = 1024
DEFAULT_OVERLAP_RATIO = 0.25
DEFAULT_MIN_EDGE_TILE = 384


def generate_overlapping_tiles(
    image_path: Path,
    output_dir: Path,
    output_slug: str,
    page: int,
    source_ref: str,
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
    min_edge_tile: int = DEFAULT_MIN_EDGE_TILE,
) -> list[dict[str, Any]]:
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError(
            "Crop generation requires Pillow. Install the environment from "
            "environment.yml before using --generate-crops."
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    overlap_px = int(tile_size * overlap_ratio)
    with Image.open(image_path) as image:
        width, height = image.size
        bboxes = generate_tile_bboxes(
            width=width,
            height=height,
            tile_size=tile_size,
            overlap_px=overlap_px,
            min_edge_tile=min_edge_tile,
        )

        tiles = []
        for index, bbox in enumerate(bboxes, start=1):
            tile_id = f"page_{page:03d}_tile_{index:03d}"
            crop_path = output_dir / f"{output_slug}_{tile_id}.png"
            crop_box = (
                bbox["x"],
                bbox["y"],
                bbox["x"] + bbox["width"],
                bbox["y"] + bbox["height"],
            )
            image.crop(crop_box).save(crop_path)
            tiles.append(
                {
                    "id": tile_id,
                    "type": "tile",
                    "page": page,
                    "bbox": bbox,
                    "source_ref": source_ref,
                    "crop_ref": str(crop_path),
                    "confidence": 1.0,
                    "tile_size_px": tile_size,
                    "overlap_px": overlap_px,
                }
            )

    return tiles


def generate_tile_bboxes(
    width: int,
    height: int,
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap_px: int | None = None,
    min_edge_tile: int = DEFAULT_MIN_EDGE_TILE,
) -> list[dict[str, int]]:
    if width <= 0 or height <= 0:
        return []

    if overlap_px is None:
        overlap_px = int(tile_size * DEFAULT_OVERLAP_RATIO)
    x_positions = generate_axis_positions(width, tile_size, overlap_px, min_edge_tile)
    y_positions = generate_axis_positions(height, tile_size, overlap_px, min_edge_tile)

    return [
        {
            "x": x,
            "y": y,
            "width": min(tile_size, width - x),
            "height": min(tile_size, height - y),
        }
        for y in y_positions
        for x in x_positions
    ]


def generate_axis_positions(
    length: int,
    tile_size: int,
    overlap_px: int,
    min_edge_tile: int,
) -> list[int]:
    if length <= tile_size:
        return [0]

    step = max(1, tile_size - overlap_px)
    positions = [0]
    while True:
        next_position = positions[-1] + step
        remaining = length - next_position
        if remaining <= tile_size:
            if remaining < min_edge_tile:
                next_position = max(0, length - tile_size)
            if next_position > positions[-1]:
                positions.append(next_position)
            break
        positions.append(next_position)

    return positions
