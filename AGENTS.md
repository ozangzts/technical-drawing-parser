# AGENTS.md

This file is the project memory for human contributors and AI coding agents. Keep it current whenever the architecture, pipeline, schema, conventions, dependencies, or major decisions change.

## Project Summary

`technical-drawing-parser` extracts structured JSON from technical drawings provided as images or PDFs. The project should handle varied drawing styles, not only pure mechanical drawings. Samples may include product renderings, dimensioned mechanical views, PCB land patterns, schematic diagrams, installation details, title blocks, logos, legal notices, tables, and notes.

The initial reference sample is:

- `DEICO_DE8135_Technical_Drawing_page-0001.jpg`

That sample includes product views, dimensions, a recommended PCB land pattern, a mounting detail, a schematic diagram, and a title block.

## Language Rules

- All project files, code, comments, prompts, schemas, logs, and documentation must be written in English.
- JSON field names must be English and use stable snake_case unless a consuming API requires another convention.

## Core Principle

Preserve evidence before interpretation.

The parser must not treat cropped regions or OCR text as the only source of truth. Every extracted value should be traceable back to the original document, page number, source coordinates, and, when available, a region crop.

Recommended evidence fields:

```json
{
  "page": 1,
  "bbox": {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0
  },
  "source_ref": "original-file.pdf#page=1",
  "crop_ref": "crops/page_001_region_001.png",
  "confidence": 0.0
}
```

## Expected Pipeline

The intended pipeline should evolve in small, testable steps:

1. Ingestion
   - Accept PDF, PNG, JPG, JPEG, and TIFF where practical.
   - Preserve the original input file.
   - Detect whether a PDF is vector-based, raster/scanned, or mixed.

2. Page Normalization
   - Convert each page to a consistent raster representation for layout work.
   - Preserve page size, DPI, coordinate mapping, and orientation metadata.
   - Avoid destructive preprocessing unless the original image remains available.

3. Layout Detection
   - Detect logical page regions before semantic extraction.
   - Store each region with `id`, `type`, `page`, `bbox`, `source_ref`, `crop_ref`, and `confidence`.
   - Region types should be extensible because drawings may vary widely.

4. Region Cropping
   - Generate crops for detected regions.
   - Keep crop coordinates tied to the original page.
   - Never discard the full page or raw region metadata.

5. OCR and Vision Extraction
   - Store raw OCR blocks with bounding boxes.
   - Use region-specific extraction where possible.
   - Treat symbols, dimensions, GD&T, electrical schematic labels, PCB pad/hole annotations, and tables as separate extraction problems.

6. Semantic Normalization
   - Normalize extracted values into stable JSON structures.
   - Preserve original text alongside normalized values when useful.
   - Include confidence and evidence references for important values.

7. Validation
   - Mark uncertain, conflicting, or incomplete fields explicitly.
   - Prefer `uncertain_fields` over silently guessing.
   - Keep raw OCR and region evidence for auditability.

8. Output
   - Produce a normalized JSON document.
   - Produce region metadata.
   - Preserve raw OCR blocks.
   - Optionally produce debug overlays for visual review.

## Initial Region Types

Use these as a starting vocabulary. Add new types as real samples require them.

- `sheet_frame`
- `coordinate_grid`
- `title_block`
- `revision_table`
- `parts_list`
- `bill_of_materials`
- `general_notes`
- `legal_notice`
- `brand_area`
- `product_view`
- `main_view`
- `side_view`
- `section_view`
- `detail_view`
- `mounting_detail`
- `recommended_land_pattern`
- `schematic_diagram`
- `dimension_annotation`
- `tolerance_annotation`
- `surface_finish_annotation`
- `gdnt_annotation`
- `weld_symbol`
- `table`
- `unknown_region`

## JSON Design Direction

Use a two-layer JSON design:

1. Normalized extraction layer
   - Clean, consumer-friendly fields such as `product_name`, `document_name`, `revision`, `scale`, `units`, `dimensions`, and `notes`.

2. Evidence layer
   - `source_regions`, `raw_ocr_blocks`, `uncertain_fields`, and field-level references that explain where each value came from.

Prefer explicit uncertainty:

```json
{
  "field": "material",
  "value": null,
  "reason": "No material callout was detected in the visible title block or notes.",
  "confidence": 0.0
}
```

## Where To Look

- New agents should start by reading `AGENTS.md`, then `README.md`, `CHANGELOG.md`, `docs/pipeline.md`, and `docs/schema.md` before making project-level changes.
- Project orientation and agent rules: `AGENTS.md`
- Change history and implementation order: `CHANGELOG.md`
- Current user-facing summary: `README.md`
- Planned pipeline and processing registry: `docs/pipeline.md`
- Initial JSON schema draft: `docs/schema.md`
- VLM extraction rules and prompt strategy: `docs/extraction.md`
- Source input location: `inputs/incoming/`
- Product JSON output location: `outputs/products/`
- Developer/internal metadata output location: `outputs/internal/`
- Recommended Conda environment file: `environment.yml`
- Local configuration template: `.env.example`
- Local CLI wrapper: `tdp.py`
- CLI entry point: `src/technical_drawing_parser/cli.py`
- Minimal pipeline implementation: `src/technical_drawing_parser/pipeline.py`
- Product extraction prompt: `src/technical_drawing_parser/extraction/prompt.py`
- Registry helpers: `src/technical_drawing_parser/registry.py`
- Reference sample drawing: `DEICO_DE8135_Technical_Drawing_page-0001.jpg`

When schema, pipeline, or folder conventions are introduced, update this section with the new locations.

## Processing Registry Rule

The parser should not process the same file content repeatedly. It should maintain `outputs/index.json`, compute a SHA-256 fingerprint for each input file, and skip files that already have a completed registry entry with the same fingerprint. At the MVP stage, each processed drawing should write one simple product JSON file under `outputs/products/` and developer-facing metadata under `outputs/internal/`.

Use these default behaviors:

- Same content already completed: skip.
- Same filename with changed content: create or overwrite the product JSON.
- Previous failed run: skip by default until retry behavior is implemented.
- `--force`: process again even when completed.
- `--retry-failed`: process failed entries again.

## Development Rules For Future Agents

- Keep all repository content in English.
- Do not commit real `.env` files or API keys. Keep `.env.example` updated when configuration changes.
- Keep `environment.yml` updated when Python dependencies or supported Python versions change.
- Update `AGENTS.md` when project structure, pipeline stages, extraction rules, schema strategy, or major assumptions change.
- Update `CHANGELOG.md` for every meaningful project change.
- Preserve original documents and coordinates whenever processing files.
- Do not delete raw OCR, source regions, or debug evidence just because a normalized JSON value was produced.
- Keep changes incremental. This project should grow through small, inspectable pipeline stages.
- Prefer structured parsers and metadata over ad hoc string manipulation.
- Add tests or sample fixtures when implementing behavior that can regress.
- If a drawing contains unexpected information, extend the schema carefully instead of forcing it into an unrelated field.

## Open TODO

- Connect a real VLM provider to fill the product JSON from image inputs.
- Continue improving the opt-in local Ollama extractor. Current local tests: `llama3.2:1b` and `moondream` run; the first `moondream` extraction call completed but failed product JSON validation; `qwen2.5vl:3b` crashes with `0xe06d7363` on the current 8 GB RAM / GTX 1050 machine.
- Validate VLM responses before writing product JSON.
- Decide how API credentials and model selection should be configured.
- Add PDF page rendering and PDF type detection.
- Add optional OCR only if it improves extraction reliability.
- Add optional layout/crop/debug artifacts only when needed.
- Add a curated sample fixture and expected product JSON once VLM extraction exists.
