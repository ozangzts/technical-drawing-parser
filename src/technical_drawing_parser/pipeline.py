from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .discovery import discover_inputs
from .fingerprint import sha256_file
from .metadata import read_file_metadata
from .extraction.ollama import DEFAULT_OLLAMA_MODEL, extract_with_ollama
from .extraction.product import empty_product_result
from .extraction.prompt import build_vlm_prompt
from .extraction.validator import parse_product_json_response
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
    extractor: str = "none",
    model: str | None = None,
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
                extractor=extractor,
                model=model,
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
    extractor: str = "none",
    model: str | None = None,
) -> dict[str, object]:
    products_dir = outputs_root / "products"
    internal_dir = outputs_root / "internal"
    products_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

    output_slug = build_output_slug(input_file.stem)
    result_path = products_dir / f"{output_slug}.json"
    internal_path = internal_dir / f"{output_slug}.internal.json"
    prompt_path = internal_dir / f"{output_slug}.vlm_prompt.txt"
    raw_response_path = internal_dir / f"{output_slug}.raw_response.txt"
    metadata = read_file_metadata(input_file)
    regions = build_initial_regions(input_file, metadata)
    processed_at = now_utc()
    result = empty_product_result(input_file)
    vlm_prompt = build_vlm_prompt(input_file)
    extraction_status = "not_run"
    extraction_error = None
    validation_warnings: list[str] = []

    if extractor == "ollama":
        extraction = extract_with_ollama(
            image_path=input_file,
            prompt=vlm_prompt,
            model=model or DEFAULT_OLLAMA_MODEL,
        )
        extraction_status = extraction.status
        extraction_error = extraction.error
        if extraction.raw_response is not None:
            write_text(raw_response_path, extraction.raw_response)
            if extraction.status == "completed":
                result, validation_warnings = parse_product_json_response(
                    extraction.raw_response,
                    input_file,
                )
                if validation_warnings:
                    extraction_status = "validation_failed"
        if extraction.status != "completed":
            result["warnings"] = [
                f"Ollama extraction failed: {extraction.error or 'unknown error'}"
            ]

    internal = build_internal_result(
        input_file=input_file,
        fingerprint=fingerprint,
        metadata=metadata,
        regions=regions,
        product_json_path=result_path,
        prompt_path=prompt_path,
        raw_response_path=raw_response_path if raw_response_path.exists() else None,
        extractor=extractor,
        model=model or (DEFAULT_OLLAMA_MODEL if extractor == "ollama" else None),
        extraction_status=extraction_status,
        extraction_error=extraction_error,
        validation_warnings=validation_warnings,
        processed_at=processed_at,
    )
    write_json(result_path, result)
    write_json(internal_path, internal)
    write_text(prompt_path, vlm_prompt)

    registry_entry = {
        "input_path": str(input_file),
        "original_filename": input_file.name,
        "fingerprint": fingerprint,
        "status": "completed",
        "result_path": str(result_path),
        "internal_path": str(internal_path),
        "prompt_path": str(prompt_path),
        "raw_response_path": str(raw_response_path) if raw_response_path.exists() else None,
        "extractor": extractor,
        "model": model or (DEFAULT_OLLAMA_MODEL if extractor == "ollama" else None),
        "extraction_status": extraction_status,
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


def build_internal_result(
    input_file: Path,
    fingerprint: str,
    metadata: dict[str, object],
    regions: list[dict[str, object]],
    product_json_path: Path,
    prompt_path: Path,
    raw_response_path: Path | None,
    extractor: str,
    model: str | None,
    extraction_status: str,
    extraction_error: str | None,
    validation_warnings: list[str],
    processed_at: str,
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "product_json_path": str(product_json_path),
        "vlm_prompt_path": str(prompt_path),
        "raw_response_path": str(raw_response_path) if raw_response_path else None,
        "extraction": {
            "extractor": extractor,
            "model": model,
            "status": extraction_status,
            "error": extraction_error,
            "validation_warnings": validation_warnings,
        },
        "document": {
            "source_path": str(input_file),
            "original_filename": input_file.name,
            "fingerprint": fingerprint,
            "metadata": metadata,
            "processed_at": processed_at,
        },
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


def build_output_slug(value: str) -> str:
    parts = slugify(value).split("_")
    noise_words = {
        "technical",
        "drawing",
        "drawings",
        "page",
        "sheet",
        "rev",
        "revision",
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "tif",
        "tiff",
    }
    useful_parts = [
        part
        for part in parts
        if part not in noise_words and not part.isdigit()
    ]

    if len(useful_parts) >= 2:
        return "_".join(useful_parts[:2])
    if useful_parts:
        return useful_parts[0]
    return slugify(value)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def write_text(path: Path, data: str) -> None:
    with path.open("w", encoding="utf-8") as file:
        file.write(data)
