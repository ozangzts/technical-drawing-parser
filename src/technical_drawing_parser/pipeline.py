from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .discovery import discover_inputs
from .fingerprint import sha256_file
from .metadata import read_file_metadata
from .registry import (
    append_registry_entry,
    find_latest_completed_entry,
    load_registry,
    save_registry,
    should_process,
)


def process_inputs(
    input_path: Path,
    outputs_root: Path,
    force: bool = False,
    retry_failed: bool = False,
) -> dict[str, int | list[str]]:
    registry_path = outputs_root / "index.json"
    registry = load_registry(registry_path)
    files = discover_inputs(input_path)
    summary: dict[str, int | list[str]] = {
        "found": len(files),
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "messages": [],
    }

    for input_file in files:
        fingerprint = sha256_file(input_file)
        process, skip_reason = should_process(
            registry=registry,
            fingerprint=fingerprint,
            force=force,
            retry_failed=retry_failed,
        )
        if not process:
            summary["skipped"] += 1
            summary["messages"].append(
                build_skip_message(input_file, skip_reason, registry, fingerprint)
            )
            continue

        try:
            output = create_product_json(
                input_file=input_file,
                fingerprint=fingerprint,
                outputs_root=outputs_root,
            )
            append_registry_entry(registry, output["registry_entry"])
            save_registry(registry_path, registry)
            summary["processed"] += 1
            summary["messages"].append(f"OK   {input_file} -> {output['result_path']}")
        except Exception as error:  # noqa: BLE001 - registry should capture failures.
            summary["failed"] += 1
            failed_entry = build_failed_entry(input_file, fingerprint, str(error))
            append_registry_entry(registry, failed_entry)
            save_registry(registry_path, registry)
            summary["messages"].append(f"FAIL {input_file} ({error})")

    return summary


def build_skip_message(
    input_file: Path,
    skip_reason: str | None,
    registry: dict[str, object],
    fingerprint: str,
) -> str:
    message = f"SKIP {input_file} ({skip_reason})"
    completed_entry = find_latest_completed_entry(registry, fingerprint)
    if completed_entry:
        result_path = completed_entry.get("result_path")
        if result_path:
            message += f" -> {result_path}"
    return message


def create_product_json(
    input_file: Path,
    fingerprint: str,
    outputs_root: Path,
) -> dict[str, object]:
    products_dir = outputs_root / "products"
    products_dir.mkdir(parents=True, exist_ok=True)

    result_path = products_dir / f"{slugify(input_file.stem)}.json"
    metadata = read_file_metadata(input_file)
    regions = build_initial_regions(input_file, metadata)
    processed_at = now_utc()
    result = build_initial_result(
        input_file=input_file,
        fingerprint=fingerprint,
        metadata=metadata,
        regions=regions,
        processed_at=processed_at,
    )
    write_json(result_path, result)

    registry_entry = {
        "input_path": str(input_file),
        "original_filename": input_file.name,
        "fingerprint": fingerprint,
        "status": "completed",
        "result_path": str(result_path),
        "processed_at": processed_at,
    }

    return {
        "result_path": str(result_path),
        "registry_entry": registry_entry,
    }


def build_initial_regions(
    input_file: Path,
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    image = metadata.get("image")
    width = image.get("width") if isinstance(image, dict) else None
    height = image.get("height") if isinstance(image, dict) else None

    bbox = None
    if isinstance(width, int) and isinstance(height, int):
        bbox = {
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
        }

    return [
        {
            "id": "page_001_region_001",
            "type": "full_page",
            "page": 1,
            "bbox": bbox,
            "source_ref": f"{input_file}#page=1",
            "crop_ref": None,
            "confidence": 1.0,
        }
    ]


def build_initial_result(
    input_file: Path,
    fingerprint: str,
    metadata: dict[str, object],
    regions: list[dict[str, object]],
    processed_at: str,
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "document": {
            "source_path": str(input_file),
            "original_filename": input_file.name,
            "fingerprint": fingerprint,
            "page_count": 1,
            "units": None,
            "metadata": metadata,
            "processed_at": processed_at,
        },
        "title_block": {
            "product_name": None,
            "document_name": None,
            "drawing_number": None,
            "revision": None,
            "revision_date": None,
            "scale": None,
            "sheet": None,
        },
        "dimensions": [],
        "notes": [],
        "regions": regions,
        "raw_ocr_blocks": [],
        "warnings": [
            "OCR, PDF rendering, layout detection, and semantic extraction are not implemented yet."
        ],
        "uncertain_fields": [
            {
                "field": "semantic_extraction",
                "value": None,
                "reason": "OCR and semantic extraction are not implemented yet.",
                "evidence": [],
                "confidence": 0.0,
            }
        ],
    }


def build_failed_entry(
    input_file: Path,
    fingerprint: str,
    error: str,
) -> dict[str, object]:
    return {
        "input_path": str(input_file),
        "original_filename": input_file.name,
        "fingerprint": fingerprint,
        "status": "failed",
        "error": error,
        "processed_at": now_utc(),
    }


def slugify(value: str) -> str:
    slug = "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    ).strip("_")
    return "_".join(part for part in slug.split("_") if part) or "drawing"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
