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

The project goal is a general technical drawing parser, not a set of fixes tuned to the current sample files. Avoid sample-specific rules such as hard-coded coordinates, product names, title-block layouts, or vendor-specific assumptions. Prefer reusable evidence, confidence, and refinement stages where OCR proposes locations, VLMs interpret visual context, and uncertain cases remain explicit instead of being silently forced into the current examples.

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
   - Clean, consumer-friendly fields such as `brand_name`, `product_name`, `document_name`, `drawing_number`, `revision`, `revision_date`, `sheet`, `size`, `scale`, `dimensions`, `dimension_tables`, `tables`, `schematics`, and `notes`.

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

Tables in product JSON should be readable without positional matching. Prefer rows with `cells` objects such as `{"column": "Signal", "value": "GND"}` instead of separate `columns` arrays plus positional `values`. For repeated side-by-side table blocks, prefer one logical item per row, such as one connector pin, one part, or one specification row.

This rule is about what the extractor (model) is asked to produce, not about the final output file. After `cells` has been parsed, the validator collapses a table to a table-level `columns` header plus per-row `values` only when every row's column sequence is provably identical — this is checked in code after parsing, not assumed from the model's output, so the earlier positional-ambiguity problem does not return. A row with a different column set, order, or length keeps the explicit `cells` shape instead. When every row's `label` is also null across a collapsed table, `label` is dropped and each row becomes a plain value array (`["1", "Analog In #1"]`); if any row's `label` carries real information (such as a numbered specification section), rows stay as `{"label": ..., "values": [...]}` objects. See `collapse_uniform_columns` in `src/technical_drawing_parser/extraction/validator.py`.

Preserve visible decimal separators in numeric strings. If the drawing shows `44,12`, keep `value` as `44,12`; do not convert it to `44.12`. Unit fields may be normalized when safe, such as `millimeters` or `millimetres` to `mm`.

Use `schematics` for circuit-level content: `{"title", "context", "components": ["R1", "R2", ...], "parameters": [{"label", "value", "context"}]}`. This is only for diagrams that show component reference designators (R1, C3, U2, ...) or a named electrical parameter repeated across the diagram (a turns ratio, a resistor value). A functional/block diagram with boxes and arrows but no reference designators or values does not get a `schematics` entry; describe it in `warnings` instead. This distinction is deliberate: it keeps the field meaningful (something was actually extractable) rather than a placeholder created for every diagram-shaped region. Do not invent a reference designator or value that is not visibly printed.

## Where To Look

- New agents should start by reading `AGENTS.md`. This file is the entry point: after reading it, the agent must also read the required context files listed in this section before making project-level changes.
- Project orientation and agent rules: `AGENTS.md`
- Change history and implementation order: `CHANGELOG.md`
- Current user-facing summary: `README.md`
- Planned pipeline and processing registry: `docs/pipeline.md`
- Initial JSON schema draft: `docs/schema.md`
- VLM extraction rules and prompt strategy: `docs/extraction.md`
- Source input location: `inputs/incoming/`
- Product JSON output location: `outputs/products/`
- Developer/internal metadata output location: `outputs/internal/`
- Compact review summary location: `outputs/internal/reviews/`
- Committed Claude Sonnet comparison outputs: `outputs_claude_sonnet_test/`
- Manual (no-API) Claude Code comparison outputs, produced by hand against the same prompt rules for cross-checking the Anthropic-run outputs above: `outputs_claude_code_sonnet5_test/`
- Golden end-to-end fixture (raw model response -> expected compact product JSON): `tests/fixtures/`, exercised by `tests/test_golden_fixture.py`
- Recommended Conda environment file: `environment.yml`
- Local configuration template: `.env.example`
- Local CLI wrapper: `tdp.py`
- CLI entry point: `src/technical_drawing_parser/cli.py`
- Minimal pipeline implementation: `src/technical_drawing_parser/pipeline.py`
- PDF page rendering helper: `src/technical_drawing_parser/pdf.py`
- Optional OCR and OCR-target crop helper: `src/technical_drawing_parser/ocr.py`
- Overlapping tile crop helper: `src/technical_drawing_parser/crops.py`
- Tile extraction duplicate summary helper: `src/technical_drawing_parser/dedupe.py`
- Product, crop, and OCR target refinement prompts: `src/technical_drawing_parser/extraction/prompt.py`
- Compact human-readable JSON serialization for product output: `src/technical_drawing_parser/json_format.py`
- Anthropic Claude extractor: `src/technical_drawing_parser/extraction/anthropic.py`
- Registry helpers: `src/technical_drawing_parser/registry.py`
- Reference sample drawing: `DEICO_DE8135_Technical_Drawing_page-0001.jpg`

When schema, pipeline, or folder conventions are introduced, update this section with the new locations.

## Processing Registry Rule

The parser should not process the same file content repeatedly. It should maintain `outputs/index.json`, compute a SHA-256 fingerprint for each input file, and skip files that already have a completed registry entry with the same fingerprint. At the MVP stage, each processed drawing should write one simple product JSON file under `outputs/products/` and developer-facing metadata under `outputs/internal/`.

Use these default behaviors:

- Same content already completed: skip.
- Same filename with changed content: create or overwrite the product JSON.
- Previous failed run without a completed entry: process again.
- `--force`: process again even when completed.
- `--retry-failed`: kept as a compatibility option; failed entries are retried by default.

## Current CLI Convention

Default processing and full-page VLM extraction do not run OCR. Use `--ocr` as the single opt-in for the OCR-assisted pipeline: local OCR, missed-value candidates, OCR target crops, VLM target refinement when supported by the extractor, and compact review output. Do not reintroduce separate user-facing commands for only generating OCR target crops or only refining OCR targets unless the pipeline design changes deliberately.

Use `--outputs <new_output_root>` for one-off model comparisons so existing output roots are preserved. The pipeline creates the requested output root automatically.

Use `--ollama-think` only for Ollama models that support thinking. Accepted values are `true`, `false`, `low`, `medium`, `high`, and `max`; model support varies.

OCR refinement and safe metadata merge helpers may remain in the codebase, but product JSON mutation from OCR-target refinement is currently paused. Until this decision changes deliberately, `outputs/products/*.json` should reflect the full-page VLM extraction result, not OCR/refinement merge output.

Both VLM extractors detect when a response was cut off at the model's output token limit (`stop_reason: max_tokens` for Anthropic, `done_reason: length` for Ollama) and mark that extraction `validation_failed` with an explicit truncation warning instead of silently accepting a possibly incomplete JSON object. See `docs/extraction.md` for details. This is a reliability safeguard only; it does not recover missing data.

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

- Continue improving the opt-in Ollama extractor. Current model results: `gemma4:cloud` gives the best extraction so far; `minicpm-v4.6` runs locally and returns valid but imperfect JSON; `moondream` runs but is not useful for extraction; `qwen2.5vl:3b`, `qwen3-vl:2b`, and local `gemma4` crash with `0xe06d7363` on the current 8 GB RAM / GTX 1050 machine. Re-ran `gemma4:cloud` on all 5 samples against the current (post-`schematics`) prompt (`outputs_ollama_gemma4cloud_test/`): it no longer crashes, and the table-collapse/compact-formatting quality is identical to the Anthropic runs because that part happens in `validator.py`/`json_format.py` regardless of which extractor produced the raw response, not in the model itself. The model's own output quality is clearly weaker than Sonnet, though, with real factual errors: wrong `revision_date` years/day-month order on two samples, an invented `"Analog Out #2"` signal name and a duplicated `"CANL"` pin value in a pinout table, a wrong current rating in a note (300 mA vs. the correct 500 mA), two tables dropped entirely (DE3000's Cell Output Connector, DE4001's Host Bus Connector), the diameter symbol rendered as `#` or `$\phi$` instead of `Ø`, `schematics.parameters` left empty on both bus-coupler samples (missed the `1:1,41` ratio entirely), and on `DE4001` it misapplied the schematic-vs-block-diagram rule by adding the "CIRCUITRY" functional block diagram to `schematics` with `"CONTROLLER"` as a fabricated "component" - the exact distinction the Claude blind-session cross-check got right on all 5 samples. Treat this as a real prompt-following capability gap in the model, not a prompt-clarity problem, since the identical prompt worked on Sonnet.
- Claude Sonnet was evaluated on the current sample PDFs and produced the strongest structured output so far, especially for readable tables and specification sections. The committed comparison outputs live under `outputs_claude_sonnet_test/`. Sonnet is expensive on 300 DPI full-page technical drawings, so prefer smaller targeted tests, cheaper models, or lower-DPI experiments before running large batches again.
- The prompt and validator changed meaningfully after the outputs under `outputs_claude_sonnet_test/` were generated (table label/column collapse, `legend_table`, the `drawing_number` vs. form-control-stamp distinction, truncated-response detection, `schematics`). Those changes were first checked by manually re-deriving product JSON by hand for comparison (see `outputs_claude_code_sonnet5_test/`), then cross-checked with a "blind" Claude Code session — a fresh session with no memory of this project's decisions, given only the literal `build_vlm_prompt()` text and the rendered image, told to answer in one shot without reading any other project file (see `outputs_claude_code_blind_test/`). All 5 samples applied the `drawing_number`/form-stamp distinction and the `schematics`/block-diagram distinction correctly and consistently, which is meaningfully closer to how the real Anthropic extractor is actually invoked (no cross-file memory, no iterative self-correction) than the first manual pass was. This is still not a real API run (different harness layer, no temperature control), so a real API run remains the only fully conclusive check, but the blind-session result meaningfully reduces how urgent that is.
- No sample seen so far (DE3000, DE8133, DE8135, DE8207, DE4001, DE12XXX) has shown any GD&T symbol, tolerance frame, or `+/-` tolerance callout. Still deliberately not designing a `tolerances` schema shape without a real sample to check it against — this session repeatedly found that a schema/rule designed without a real example needed correction once one appeared (`schematics.parameters` consolidation, the `drawing_number` vs. form-stamp split). As a cheap safety net against the blind spot this creates, the prompt does ask the model to describe a GD&T feature control frame or `+/-` callout in `warnings` if it ever sees one, instead of forcing it into `dimensions` or silently dropping it; `tolerances` itself stays an empty placeholder until a real sample justifies a shape for it.
- `schematics` (component reference designators and named electrical parameters from circuit-level diagrams) was added after schematic content showed up in most samples (DE8135, DE8133, DE8207) as the same bus-coupler topology scaled by stub count (3/5/7), each time only described in a free-text `warnings` entry instead of being queryable/comparable across the family. Functional/block diagrams without reference designators (DE3000, DE4001) intentionally do not get a `schematics` entry. The blind-session test (see previous bullet) confirmed the block-diagram-vs-schematic distinction on all 5 samples, and also surfaced a real gap: it produced one repeated `parameters` entry per stub instead of one consolidated entry, which is now covered by a prompt rule. Not yet seen on a drawing with per-component values (only reference designators and network-level parameters so far).
- Add merge behavior for multi-page PDF page-level extraction. Still untested: every sample so far has been a single page.
- Add PDF type detection (vector vs. raster vs. mixed).
- Continue evaluating OCR target refinement quality. Safe metadata merge code exists but is paused for product JSON output; dimension merge is not implemented yet.
- Add crop extraction merge and dedupe using page-space tile coordinates. This path (`--generate-crops`/`--extract-crops`) is currently Ollama-only and its results are not merged into product JSON.
- Add layout detection only when needed.
