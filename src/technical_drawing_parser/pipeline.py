from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .discovery import discover_inputs
from .fingerprint import sha256_file
from .metadata import read_file_metadata
from .registry import append_registry_entry, load_registry, save_registry, should_process


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
            summary["messages"].append(f"SKIP {input_file} ({skip_reason})")
            continue

        try:
            run = create_run(
                input_file=input_file,
                fingerprint=fingerprint,
                outputs_root=outputs_root,
            )
            append_registry_entry(registry, run["registry_entry"])
            save_registry(registry_path, registry)
            summary["processed"] += 1
            summary["messages"].append(f"OK   {input_file} -> {run['run_dir']}")
        except Exception as error:  # noqa: BLE001 - registry should capture failures.
            summary["failed"] += 1
            failed_entry = build_failed_entry(input_file, fingerprint, str(error))
            append_registry_entry(registry, failed_entry)
            save_registry(registry_path, registry)
            summary["messages"].append(f"FAIL {input_file} ({error})")

    return summary


def create_run(
    input_file: Path,
    fingerprint: str,
    outputs_root: Path,
) -> dict[str, object]:
    started_at = now_utc()
    run_id = build_run_id(input_file, started_at)
    run_dir = outputs_root / "runs" / run_id
    input_dir = run_dir / "input"
    regions_dir = run_dir / "regions"

    input_dir.mkdir(parents=True, exist_ok=False)
    regions_dir.mkdir(parents=True, exist_ok=True)
    for name in ("pages", "crops", "debug", "ocr"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)

    copied_input = input_dir / input_file.name
    shutil.copy2(input_file, copied_input)

    metadata = read_file_metadata(copied_input)
    regions = build_initial_regions(copied_input, metadata)
    write_json(regions_dir / "page_001_regions.json", {"regions": regions})

    completed_at = now_utc()
    manifest = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "input": {
            "original_path": str(input_file),
            "copied_path": str(copied_input),
            "original_filename": input_file.name,
            "fingerprint": fingerprint,
            "metadata": metadata,
        },
        "outputs": {
            "result": "result.json",
            "regions": "regions/page_001_regions.json",
            "warnings": "warnings.json",
        },
    }
    result = build_initial_result(
        input_file=input_file,
        fingerprint=fingerprint,
        metadata=metadata,
        regions=regions,
    )
    warnings = {
        "warnings": [
            "OCR, PDF rendering, layout detection, and semantic extraction are not implemented yet."
        ]
    }

    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "result.json", result)
    write_json(run_dir / "warnings.json", warnings)

    registry_entry = {
        "input_path": str(input_file),
        "original_filename": input_file.name,
        "fingerprint": fingerprint,
        "status": "completed",
        "latest_run_id": run_id,
        "result_path": str(run_dir / "result.json"),
        "processed_at": completed_at,
    }

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "registry_entry": registry_entry,
    }


def build_initial_regions(
    copied_input: Path,
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
            "source_ref": f"input/{copied_input.name}#page=1",
            "crop_ref": None,
            "confidence": 1.0,
        }
    ]


def build_initial_result(
    input_file: Path,
    fingerprint: str,
    metadata: dict[str, object],
    regions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "document": {
            "original_filename": input_file.name,
            "fingerprint": fingerprint,
            "page_count": 1,
            "units": None,
            "metadata": metadata,
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


def build_run_id(input_file: Path, timestamp: str) -> str:
    safe_name = "".join(
        character.lower() if character.isalnum() else "_"
        for character in input_file.stem
    ).strip("_")
    safe_name = "_".join(part for part in safe_name.split("_") if part)
    timestamp_prefix = timestamp.replace("-", "").replace(":", "")[:15] + "Z"
    return f"{timestamp_prefix}_{safe_name}"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
