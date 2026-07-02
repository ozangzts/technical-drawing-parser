"""Input discovery helpers for supported technical drawing files."""

from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def discover_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if is_supported_input(input_path) else []

    if not input_path.exists():
        return []

    files = [
        path
        for path in input_path.rglob("*")
        if path.is_file() and is_supported_input(path)
    ]
    return sorted(files, key=lambda path: str(path).lower())


def is_supported_input(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
