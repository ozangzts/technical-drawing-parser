from __future__ import annotations

import struct
from pathlib import Path


def read_file_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
    }

    image_size = read_image_size(path)
    if image_size:
        width, height = image_size
        metadata["image"] = {
            "width": width,
            "height": height,
        }

    if path.suffix.lower() == ".pdf":
        metadata["pdf"] = {
            "page_count": None,
            "note": "PDF page rendering is not implemented yet.",
        }

    return metadata


def read_image_size(path: Path) -> tuple[int, int] | None:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return read_png_size(path)
    if suffix in {".jpg", ".jpeg"}:
        return read_jpeg_size(path)
    return None


def read_png_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def read_jpeg_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as file:
        if file.read(2) != b"\xff\xd8":
            return None

        while True:
            marker_prefix = file.read(1)
            if not marker_prefix:
                return None
            if marker_prefix != b"\xff":
                continue

            marker = file.read(1)
            while marker == b"\xff":
                marker = file.read(1)
            if not marker:
                return None

            marker_value = marker[0]
            if marker_value in {0xD8, 0xD9}:
                continue

            length_bytes = file.read(2)
            if len(length_bytes) != 2:
                return None
            segment_length = struct.unpack(">H", length_bytes)[0]
            if segment_length < 2:
                return None

            if marker_value in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                data = file.read(5)
                if len(data) != 5:
                    return None
                height, width = struct.unpack(">HH", data[1:5])
                return int(width), int(height)

            file.seek(segment_length - 2, 1)

