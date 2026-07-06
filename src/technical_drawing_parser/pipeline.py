"""Main batch-processing flow from input drawings to product JSON outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .crops import generate_overlapping_tiles
from .dedupe import build_tile_extraction_summary
from .discovery import discover_inputs
from .fingerprint import sha256_file
from .metadata import read_file_metadata
from .ocr import (
    DEFAULT_OCR_ENGINE,
    build_comparison_values,
    build_ocr_candidates,
    build_ocr_target_crops,
    normalize_ocr_value,
    run_ocr_pages,
)
from .extraction.ollama import DEFAULT_OLLAMA_MODEL, extract_with_ollama
from .extraction.product import empty_product_result
from .extraction.prompt import (
    build_ocr_target_refinement_prompt,
    build_tile_vlm_prompt,
    build_vlm_prompt,
)
from .extraction.validator import (
    parse_ocr_target_refinement_response,
    parse_product_json_response,
)
from .pdf import render_pdf_pages
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
    generate_crops: bool = False,
    extract_crops: bool = False,
    run_ocr: bool = False,
    ocr_engine: str = DEFAULT_OCR_ENGINE,
    generate_ocr_target_crops: bool = False,
    refine_ocr_targets: bool = False,
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
                generate_crops=generate_crops,
                extract_crops=extract_crops,
                run_ocr=run_ocr or generate_ocr_target_crops or refine_ocr_targets,
                ocr_engine=ocr_engine,
                generate_ocr_target_crops=generate_ocr_target_crops
                or refine_ocr_targets,
                refine_ocr_targets=refine_ocr_targets,
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
    generate_crops: bool = False,
    extract_crops: bool = False,
    run_ocr: bool = False,
    ocr_engine: str = DEFAULT_OCR_ENGINE,
    generate_ocr_target_crops: bool = False,
    refine_ocr_targets: bool = False,
) -> dict[str, object]:
    generate_ocr_target_crops = generate_ocr_target_crops or refine_ocr_targets
    run_ocr = run_ocr or generate_ocr_target_crops
    products_dir = outputs_root / "products"
    internal_dir = outputs_root / "internal"
    products_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

    output_slug = build_output_slug(input_file.stem)
    result_path = products_dir / f"{output_slug}.json"
    internal_path = internal_dir / f"{output_slug}.internal.json"
    tile_summary_path = internal_dir / f"{output_slug}.tile_summary.json"
    prompt_path = internal_dir / f"{output_slug}.vlm_prompt.txt"
    raw_response_path = internal_dir / f"{output_slug}.raw_response.txt"
    metadata = read_file_metadata(input_file)
    rendered_pages: list[dict[str, object]] = []
    processing_warnings: list[str] = []
    if input_file.suffix.lower() == ".pdf":
        rendered_pages = render_pdf_pages(
            input_file,
            internal_dir / "page_images",
            output_slug,
        )
        first_rendered_page = rendered_pages[0]
        metadata["rendered_pages"] = rendered_pages
        metadata["image"] = {
            "width": first_rendered_page["width"],
            "height": first_rendered_page["height"],
            "derived_from": str(input_file),
            "page": 1,
        }
        if len(rendered_pages) > 1:
            processing_warnings.append(
                "PDF has multiple pages; product JSON uses page 1 until merge behavior is implemented."
            )
    regions = build_initial_regions(input_file, metadata)
    page_source_images = build_tile_source_images(input_file, metadata)
    raw_ocr_blocks: list[dict[str, object]] = []
    if run_ocr:
        raw_ocr_blocks = run_ocr_pages(
            page_source_images,
            engine_name=ocr_engine,
        )
    tiles: list[dict[str, object]] = []
    if generate_crops or extract_crops:
        tiles = build_page_tiles(
            input_file=input_file,
            output_slug=output_slug,
            internal_dir=internal_dir,
            metadata=metadata,
        )
    processed_at = now_utc()
    result = empty_product_result(input_file)
    vlm_prompt = build_vlm_prompt(input_file)
    extraction_status = "not_run"
    extraction_error = None
    validation_warnings: list[str] = []
    page_extractions: list[dict[str, object]] = []
    tile_extractions: list[dict[str, object]] = []
    ocr_target_refinements: list[dict[str, object]] = []

    if extractor == "ollama":
        extraction_inputs = build_extraction_inputs(
            input_file=input_file,
            rendered_pages=rendered_pages,
        )
        for extraction_input in extraction_inputs:
            page_extraction = run_ollama_page_extraction(
                image_path=extraction_input["image_path"],
                page=int(extraction_input["page"]),
                prompt=vlm_prompt,
                input_file=input_file,
                raw_response_path=build_page_raw_response_path(
                    raw_response_path,
                    int(extraction_input["page"]),
                ),
                model=model or DEFAULT_OLLAMA_MODEL,
            )
            page_extractions.append(page_extraction)

            if page_extraction["page"] == 1:
                extraction_status = str(page_extraction["status"])
                extraction_error = page_extraction.get("error")
                validation_warnings = list(page_extraction["validation_warnings"])
                parsed_result = page_extraction.get("product_json")
                if isinstance(parsed_result, dict):
                    result = parsed_result

        if extraction_status not in {"completed", "validation_failed"}:
            result["warnings"] = [
                f"Ollama extraction failed: {extraction_error or 'unknown error'}"
            ]
        if extract_crops:
            tile_extractions = run_ollama_tile_extractions(
                tiles=tiles,
                source_file=input_file,
                internal_dir=internal_dir,
                output_slug=output_slug,
                model=model or DEFAULT_OLLAMA_MODEL,
            )
    elif extract_crops:
        processing_warnings.append(
            "Crop extraction was requested but skipped because no VLM extractor is enabled."
        )
    result["warnings"].extend(processing_warnings)
    ocr_candidates = build_ocr_candidates(raw_ocr_blocks, result)
    ocr_target_crops: list[dict[str, object]] = []
    if generate_ocr_target_crops:
        ocr_target_crops = build_ocr_target_crops(
            ocr_candidates=ocr_candidates,
            page_images=page_source_images,
            output_dir=internal_dir / "ocr_target_crops",
            output_slug=output_slug,
        )
    if refine_ocr_targets:
        if extractor == "ollama":
            ocr_target_refinements = run_ollama_ocr_target_refinements(
                targets=ocr_target_crops,
                source_file=input_file,
                internal_dir=internal_dir,
                output_slug=output_slug,
                model=model or DEFAULT_OLLAMA_MODEL,
            )
        else:
            processing_warnings.append(
                "OCR target refinement was requested but skipped because no VLM extractor is enabled."
            )

    internal = build_internal_result(
        input_file=input_file,
        fingerprint=fingerprint,
        metadata=metadata,
        regions=regions,
        raw_ocr_blocks=raw_ocr_blocks,
        ocr_candidates=ocr_candidates,
        ocr_target_crops=ocr_target_crops,
        ocr_target_refinements=ocr_target_refinements,
        tiles=tiles,
        product_json_path=result_path,
        tile_summary_path=tile_summary_path,
        prompt_path=prompt_path,
        raw_response_path=raw_response_path if raw_response_path.exists() else None,
        rendered_pages=rendered_pages,
        page_extractions=page_extractions,
        tile_extractions=tile_extractions,
        extractor=extractor,
        model=model or (DEFAULT_OLLAMA_MODEL if extractor == "ollama" else None),
        extraction_status=extraction_status,
        extraction_error=extraction_error,
        validation_warnings=validation_warnings,
        processing_warnings=processing_warnings,
        processed_at=processed_at,
    )
    write_json(result_path, result)
    write_json(internal_path, internal)
    write_json(tile_summary_path, internal["tile_extraction_summary"])
    write_text(prompt_path, vlm_prompt)

    registry_entry = {
        "input_path": str(input_file),
        "original_filename": input_file.name,
        "fingerprint": fingerprint,
        "status": "completed",
        "result_path": str(result_path),
        "internal_path": str(internal_path),
        "tile_summary_path": str(tile_summary_path),
        "prompt_path": str(prompt_path),
        "raw_response_path": str(raw_response_path) if raw_response_path.exists() else None,
        "extractor": extractor,
        "ocr_engine": ocr_engine if run_ocr else None,
        "ocr_target_crops": generate_ocr_target_crops,
        "ocr_target_refinements": refine_ocr_targets,
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
    rendered_pages = metadata.get("rendered_pages")
    if isinstance(rendered_pages, list) and rendered_pages:
        return [
            build_full_page_region(input_file, rendered_page)
            for rendered_page in rendered_pages
            if isinstance(rendered_page, dict)
        ]

    image = metadata.get("image")
    return [build_full_page_region(input_file, {"page": 1, "image": image})]


def build_page_tiles(
    input_file: Path,
    output_slug: str,
    internal_dir: Path,
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    page_images = build_tile_source_images(input_file, metadata)
    tiles: list[dict[str, object]] = []
    for page_image in page_images:
        tiles.extend(
            generate_overlapping_tiles(
                image_path=Path(str(page_image["image_path"])),
                output_dir=internal_dir / "crops",
                output_slug=output_slug,
                page=int(page_image["page"]),
                source_ref=str(page_image["source_ref"]),
            )
        )
    return tiles


def build_tile_source_images(
    input_file: Path,
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    rendered_pages = metadata.get("rendered_pages")
    if isinstance(rendered_pages, list) and rendered_pages:
        return [
            {
                "page": rendered_page.get("page", 1),
                "image_path": rendered_page["path"],
                "source_ref": f"{input_file}#page={rendered_page.get('page', 1)}",
            }
            for rendered_page in rendered_pages
            if isinstance(rendered_page, dict) and "path" in rendered_page
        ]

    return [
        {
            "page": 1,
            "image_path": input_file,
            "source_ref": f"{input_file}#page=1",
        }
    ]


def build_full_page_region(
    input_file: Path,
    page_metadata: dict[str, object],
) -> dict[str, object]:
    page = page_metadata.get("page")
    page_number = page if isinstance(page, int) else 1
    width = page_metadata.get("width")
    height = page_metadata.get("height")
    image = page_metadata.get("image")
    if isinstance(image, dict):
        width = image.get("width")
        height = image.get("height")

    bbox = None
    if isinstance(width, int) and isinstance(height, int):
        bbox = {
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
        }

    return {
        "id": f"page_{page_number:03d}_region_001",
        "type": "full_page",
        "page": page_number,
        "bbox": bbox,
        "source_ref": f"{input_file}#page={page_number}",
        "crop_ref": None,
        "confidence": 1.0,
    }


def build_extraction_inputs(
    input_file: Path,
    rendered_pages: list[dict[str, object]],
) -> list[dict[str, object]]:
    if rendered_pages:
        return [
            {
                "page": rendered_page.get("page", 1),
                "image_path": Path(str(rendered_page["path"])),
            }
            for rendered_page in rendered_pages
            if "path" in rendered_page
        ]

    return [
        {
            "page": 1,
            "image_path": input_file,
        }
    ]


def build_page_raw_response_path(raw_response_path: Path, page: int) -> Path:
    if page == 1:
        return raw_response_path
    base_stem = raw_response_path.stem
    if base_stem.endswith(".raw_response"):
        base_stem = base_stem.removesuffix(".raw_response")
    return raw_response_path.with_name(
        f"{base_stem}_page_{page:03d}.raw_response{raw_response_path.suffix}"
    )


def run_ollama_page_extraction(
    image_path: Path,
    page: int,
    prompt: str,
    input_file: Path,
    raw_response_path: Path,
    model: str,
) -> dict[str, object]:
    extraction = extract_with_ollama(
        image_path=image_path,
        prompt=prompt,
        model=model,
    )
    validation_warnings: list[str] = []
    product_json = None
    status = extraction.status

    if extraction.raw_response is not None:
        write_text(raw_response_path, extraction.raw_response)
        if extraction.status == "completed":
            product_json, validation_warnings = parse_product_json_response(
                extraction.raw_response,
                input_file,
            )
            if validation_warnings:
                status = "validation_failed"

    return {
        "page": page,
        "image_path": str(image_path),
        "raw_response_path": str(raw_response_path)
        if extraction.raw_response is not None
        else None,
        "status": status,
        "error": extraction.error,
        "validation_warnings": validation_warnings,
        "product_json": product_json,
    }


def run_ollama_tile_extractions(
    tiles: list[dict[str, object]],
    source_file: Path,
    internal_dir: Path,
    output_slug: str,
    model: str,
) -> list[dict[str, object]]:
    tile_extractions = []
    for tile in tiles:
        crop_ref = tile.get("crop_ref")
        tile_id = tile.get("id")
        if not isinstance(crop_ref, str) or not isinstance(tile_id, str):
            continue

        raw_response_path = build_tile_raw_response_path(
            internal_dir=internal_dir,
            output_slug=output_slug,
            tile_id=tile_id,
        )
        prompt = build_tile_vlm_prompt(source_file, tile)
        extraction = extract_with_ollama(
            image_path=Path(crop_ref),
            prompt=prompt,
            model=model,
        )
        validation_warnings: list[str] = []
        product_json = None
        status = extraction.status

        if extraction.raw_response is not None:
            write_text(raw_response_path, extraction.raw_response)
            if extraction.status == "completed":
                product_json, validation_warnings = parse_product_json_response(
                    extraction.raw_response,
                    source_file,
                )
                if validation_warnings:
                    status = "validation_failed"

        tile_extractions.append(
            {
                "tile_id": tile_id,
                "page": tile.get("page"),
                "bbox": tile.get("bbox"),
                "crop_ref": crop_ref,
                "raw_response_path": str(raw_response_path)
                if extraction.raw_response is not None
                else None,
                "status": status,
                "error": extraction.error,
                "validation_warnings": validation_warnings,
                "product_json": product_json,
            }
        )

    return tile_extractions


def run_ollama_ocr_target_refinements(
    targets: list[dict[str, object]],
    source_file: Path,
    internal_dir: Path,
    output_slug: str,
    model: str,
) -> list[dict[str, object]]:
    refinements = []
    for target in targets:
        crop_ref = target.get("crop_ref")
        target_id = target.get("id")
        if not isinstance(crop_ref, str) or not isinstance(target_id, str):
            continue

        raw_response_path = build_ocr_target_raw_response_path(
            internal_dir=internal_dir,
            output_slug=output_slug,
            target_id=target_id,
        )
        prompt = build_ocr_target_refinement_prompt(source_file, target)
        extraction = extract_with_ollama(
            image_path=Path(crop_ref),
            prompt=prompt,
            model=model,
        )
        validation_warnings: list[str] = []
        refinement_json = None
        status = extraction.status

        if extraction.raw_response is not None:
            write_text(raw_response_path, extraction.raw_response)
            if extraction.status == "completed":
                refinement_json, validation_warnings = (
                    parse_ocr_target_refinement_response(
                        extraction.raw_response,
                        target,
                    )
                )
                if validation_warnings:
                    status = "validation_failed"

        refinements.append(
            {
                "target_id": target_id,
                "page": target.get("page"),
                "bbox": target.get("bbox"),
                "ocr_bbox": target.get("ocr_bbox"),
                "ocr_text": target.get("text"),
                "crop_ref": crop_ref,
                "raw_response_path": str(raw_response_path)
                if extraction.raw_response is not None
                else None,
                "status": status,
                "error": extraction.error,
                "validation_warnings": validation_warnings,
                "refinement_json": refinement_json,
            }
        )

    return refinements


def build_tile_raw_response_path(
    internal_dir: Path,
    output_slug: str,
    tile_id: str,
) -> Path:
    return internal_dir / "tile_responses" / f"{output_slug}_{tile_id}.raw_response.txt"


def build_ocr_target_raw_response_path(
    internal_dir: Path,
    output_slug: str,
    target_id: str,
) -> Path:
    return (
        internal_dir
        / "ocr_target_responses"
        / f"{output_slug}_{target_id}.raw_response.txt"
    )


def build_internal_result(
    input_file: Path,
    fingerprint: str,
    metadata: dict[str, object],
    regions: list[dict[str, object]],
    raw_ocr_blocks: list[dict[str, object]],
    ocr_candidates: list[dict[str, object]],
    ocr_target_crops: list[dict[str, object]],
    ocr_target_refinements: list[dict[str, object]],
    tiles: list[dict[str, object]],
    product_json_path: Path,
    tile_summary_path: Path,
    prompt_path: Path,
    raw_response_path: Path | None,
    rendered_pages: list[dict[str, object]],
    page_extractions: list[dict[str, object]],
    tile_extractions: list[dict[str, object]],
    extractor: str,
    model: str | None,
    extraction_status: str,
    extraction_error: str | None,
    validation_warnings: list[str],
    processing_warnings: list[str],
    processed_at: str,
) -> dict[str, object]:
    warnings = [
        "Layout detection, product merge from refinement results, and region-specific semantic extraction are not implemented yet."
    ]
    warnings.extend(processing_warnings)
    tile_extraction_summary = build_tile_extraction_summary(
        tile_extractions,
        full_page_product_json=page_extractions[0]["product_json"]
        if page_extractions
        and isinstance(page_extractions[0].get("product_json"), dict)
        else None,
    )
    full_page_product_json = (
        page_extractions[0]["product_json"]
        if page_extractions
        and isinstance(page_extractions[0].get("product_json"), dict)
        else None
    )

    return {
        "schema_version": "0.1.0",
        "product_json_path": str(product_json_path),
        "tile_summary_path": str(tile_summary_path),
        "vlm_prompt_path": str(prompt_path),
        "raw_response_path": str(raw_response_path) if raw_response_path else None,
        "rendered_page": rendered_pages[0] if rendered_pages else None,
        "rendered_pages": rendered_pages,
        "page_extractions": page_extractions,
        "tile_extractions": tile_extractions,
        "tile_extraction_summary": tile_extraction_summary,
        "ocr_target_refinement_summary": build_ocr_target_refinement_summary(
            ocr_target_refinements,
            full_page_product_json=full_page_product_json,
        ),
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
        "tiles": tiles,
        "raw_ocr_blocks": raw_ocr_blocks,
        "ocr_candidates": ocr_candidates,
        "ocr_target_crops": ocr_target_crops,
        "ocr_target_refinements": ocr_target_refinements,
        "warnings": warnings,
        "uncertain_fields": [
            {
                "field": "semantic_extraction",
                "value": None,
                "reason": "Product JSON merge from OCR target refinement and region-specific semantic extraction are not implemented yet.",
                "evidence": [],
                "confidence": 0.0,
            }
        ],
    }


def build_ocr_target_refinement_summary(
    refinements: list[dict[str, object]],
    full_page_product_json: dict[str, object] | None = None,
) -> dict[str, object]:
    product_coverage = build_product_dimension_coverage(full_page_product_json)
    summary = {
        "targets": len(refinements),
        "dimensions": 0,
        "metadata": 0,
        "notes": 0,
        "uncertain": 0,
        "irrelevant": 0,
        "failed": 0,
        "merge_candidates": [],
        "covered_by_dimensions": [],
        "covered_by_dimension_tables": [],
        "new_dimension_candidates": [],
        "metadata_review_candidates": [],
    }

    for refinement in refinements:
        if refinement.get("status") not in {"completed", "validation_failed"}:
            summary["failed"] += 1
            continue

        refinement_json = refinement.get("refinement_json")
        if not isinstance(refinement_json, dict):
            summary["uncertain"] += 1
            continue

        classification = refinement_json.get("classification")
        if classification == "dimension":
            summary["dimensions"] += 1
            if refinement_json.get("is_product_dimension") is True:
                candidate = build_refinement_merge_candidate(
                    refinement,
                    refinement_json,
                    product_coverage,
                )
                summary["merge_candidates"].append(candidate)
                if candidate["coverage"] == "dimensions":
                    summary["covered_by_dimensions"].append(candidate)
                elif candidate["coverage"] == "dimension_tables":
                    summary["covered_by_dimension_tables"].append(candidate)
                else:
                    summary["new_dimension_candidates"].append(candidate)
        elif classification == "metadata":
            summary["metadata"] += 1
            metadata_candidate = build_metadata_review_candidate(
                refinement,
                refinement_json,
                full_page_product_json,
            )
            if metadata_candidate:
                summary["metadata_review_candidates"].append(metadata_candidate)
        elif classification == "note":
            summary["notes"] += 1
        elif classification == "irrelevant":
            summary["irrelevant"] += 1
        else:
            summary["uncertain"] += 1

    return summary


def build_metadata_review_candidate(
    refinement: dict[str, object],
    refinement_json: dict[str, object],
    product_json: dict[str, object] | None,
) -> dict[str, object] | None:
    metadata = refinement_json.get("metadata")
    if not isinstance(metadata, dict):
        return None

    field = normalize_metadata_field(metadata.get("field"))
    value = metadata.get("value")
    if field is None or value is None:
        return None

    product_value = product_json.get(field) if isinstance(product_json, dict) else None
    normalized_refinement_value = normalize_metadata_value(value)
    normalized_product_value = normalize_metadata_value(product_value)
    status = (
        "supported"
        if normalized_product_value
        and normalized_refinement_value == normalized_product_value
        else "conflict"
        if normalized_product_value
        else "missing_in_product"
    )

    return {
        "target_id": refinement.get("target_id"),
        "ocr_text": refinement.get("ocr_text"),
        "field": field,
        "product_value": product_value,
        "refinement_value": value,
        "confidence": refinement_json.get("confidence"),
        "status": status,
    }


def normalize_metadata_field(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    normalized = normalized.replace(".", "")
    normalized = normalized.replace("_", " ")
    normalized = " ".join(normalized.split())
    field_aliases = {
        "scale": "scale",
        "drawing scale": "scale",
        "size": "size",
        "sheet size": "size",
        "revision": "revision",
        "rev": "revision",
        "revision date": "revision_date",
        "rev date": "revision_date",
        "date": "revision_date",
        "sheet": "sheet",
        "sheet number": "sheet",
        "sheet no": "sheet",
    }
    return field_aliases.get(normalized)


def normalize_metadata_value(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    normalized = normalized.replace(",", ".")
    normalized = " ".join(normalized.split())
    return normalized or None


def build_refinement_merge_candidate(
    refinement: dict[str, object],
    refinement_json: dict[str, object],
    product_coverage: dict[str, set[str]],
) -> dict[str, object]:
    dimension = refinement_json.get("dimension")
    candidate_values = collect_dimension_comparison_values(dimension)
    if candidate_values.intersection(product_coverage["dimensions"]):
        coverage = "dimensions"
    elif candidate_values.intersection(product_coverage["dimension_tables"]):
        coverage = "dimension_tables"
    else:
        coverage = "new"

    return {
        "target_id": refinement.get("target_id"),
        "ocr_text": refinement.get("ocr_text"),
        "dimension": dimension,
        "confidence": refinement_json.get("confidence"),
        "coverage": coverage,
    }


def build_product_dimension_coverage(
    product_json: dict[str, object] | None,
) -> dict[str, set[str]]:
    coverage = {
        "dimensions": set(),
        "dimension_tables": set(),
    }
    if not isinstance(product_json, dict):
        return coverage

    dimensions = product_json.get("dimensions")
    if isinstance(dimensions, list):
        for dimension in dimensions:
            coverage["dimensions"].update(
                collect_dimension_comparison_values(dimension)
            )

    dimension_tables = product_json.get("dimension_tables")
    if isinstance(dimension_tables, list):
        for table in dimension_tables:
            if not isinstance(table, dict):
                continue
            rows = table.get("rows")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                values = row.get("values")
                if not isinstance(values, list):
                    continue
                for value in values:
                    coverage["dimension_tables"].update(
                        collect_scalar_comparison_values(value)
                    )

    return coverage


def collect_dimension_comparison_values(dimension: object) -> set[str]:
    values: set[str] = set()
    if not isinstance(dimension, dict):
        return values

    for field in ("raw_text", "value"):
        values.update(collect_scalar_comparison_values(dimension.get(field)))
    return values


def collect_scalar_comparison_values(value: object) -> set[str]:
    if value is None:
        return set()
    return build_comparison_values(normalize_ocr_value(str(value)))


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write(data)
