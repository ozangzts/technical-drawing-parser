# Changelog

All notable changes to this project should be documented in this file.

The format is inspired by Keep a Changelog, and this project uses chronological entries while the project is still in early exploration.

## 2026-07-09

### Added

- Clarified `label` versus `context` for dimension objects: `label` is a short, reusable category for what kind of measurement this is (`hole diameter`, `overall width`), `context` is where this specific instance is (`recommended land pattern`, `front view`). Real Anthropic-run output showed this wasn't followed consistently (`label` left `null` for every dimension on some drawings, invented on others, and on one drawing set to `"R10"` — a plain echo of `raw_text`). Added a clearer prompt rule plus a validator safety net (`drop_label_redundant_with_dimension_value`) that nulls out a `label` exactly matching `raw_text` or `value`.
- Clarified when a dimension's `type` should be `pattern` versus `linear`: `pattern` is for a repeated center-to-center spacing or pitch (a pin pitch, a hole pitch), `linear` is for a single, non-repeated straight-line measurement, even if it also carries a quantity marker. Comparing manual extractions against the existing Anthropic-run outputs showed the model choosing `pattern` for a pitch dimension on one sample and `linear` for the same kind of pitch dimension on a sibling sample; the validator's existing `pitch -> pattern` alias only helps when the model's `type` string is literally `pitch`, not when it directly guesses `linear`, so the rule needed to live in the prompt.
- Added a `schematics` product JSON field for circuit-level diagrams: `{"title", "context", "components": ["R1", ...], "parameters": [{"label", "value", "context"}]}`. Only diagrams with visible component reference designators or a named electrical parameter repeated across the diagram qualify; a functional/block diagram with only boxes and arrows (no reference designators or values) stays described in `warnings` instead, so the field is never forced onto content it can't add structure to. Added `normalize_schematics`/`normalize_schematic_parameters` in `validator.py`, prompt rules shared between the full-page and tile prompts, and extended the golden fixture to cover it end to end.
- Added a golden end-to-end regression fixture (`tests/fixtures/sample_raw_response.json` and `tests/fixtures/expected_product.json`, exercised by `tests/test_golden_fixture.py`) that locks in `parse_product_json_response` and `format_json_compact` working together: table label dropping, the uniform-columns collapse, the non-uniform fallback, and the compact rendering all in one checked example. This was the last open item in this file's "Add a curated sample fixture" TODO.
- Updated `AGENTS.md`'s Open TODO to reflect this session's findings: marked the `size`/`scale`/dimension-type normalization item done (already implemented in `validator.py`), noted that schematic/circuit diagrams are now a recurring, evidence-backed content gap across most samples (not yet designed), and noted that the new prompt/validator rules have only been checked by hand, not against a real Anthropic API run.

- Added truncated-response detection for the Anthropic and Ollama extractors: a response cut off at the model's output token limit (`stop_reason: max_tokens` / `done_reason: length`) is now marked `validation_failed` with an explicit warning instead of silently risking a JSON object that parses cleanly but is missing trailing fields such as later tables, notes, or warnings.
- Added unit tests for the new truncation-detection helpers in both extractors.
- Added a table normalization rule that drops a row `label` when it only restates the row's first `cells` value (such as `label: "Pin 1"` next to a `Pin Number: 1` cell), so pinout/connection-style tables stop repeating the same value in two places. Labels that carry information beyond the first cell, such as numbered specification sections, are unaffected.
- Added `src/technical_drawing_parser/json_format.py` and switched `outputs/products/*.json` to it: short, uniform rows (dimensions, table rows) now render on one line each instead of one line per key, while long values still expand so nothing is truncated. This is formatting only; the underlying JSON values and structure are unchanged. Internal/debug JSON output is unaffected.
- Added a table normalization step (`collapse_uniform_columns` in `validator.py`) that collapses a table's rows to a table-level `columns` header plus per-row `values` when every row (at least two) shares the exact same column sequence, removing repeated column names such as `"Pin Number"` on every one of 25 pinout rows. Uniformity is verified from the already-parsed `cells`, not assumed from the model's output, so an irregular table keeps the explicit `cells` shape. Rows also drop `label` entirely (becoming a plain value array) when every row's label is null across the table; labels that carry real information keep a `{"label": ..., "values": [...]}` row shape.
- Added `legend_table` to the `type` enum shown to the model in `product_schema_description()`. Prompts already told the model to put legend/notation tables in `tables`, and the validator already accepted `legend_table` as a type, but the model was never actually offered that value to choose from, so a legend table could only ever come back as `unknown`.
- Added a rule asking the model to use the same column order in every row of a multi-row table, so the new `collapse_uniform_columns` step has a better chance of finding a table's rows provably uniform instead of falling back to the verbose `cells` shape.
- Extracted the rule text shared verbatim between `build_vlm_prompt` and `build_tile_vlm_prompt` into named constants in `prompt.py` so the two prompts cannot silently drift apart on wording that was never meant to differ. Verified the rendered prompt text is unchanged from before the refactor (code-organization change only).
- Clarified `drawing_number` extraction: a short product/model code (such as `DE4001`) should be extracted into `drawing_number` even when it only appears embedded inside `product_name` or `document_name` text, but a generic document/form control stamp that carries its own separate revision and date (such as `SBL-0033 Rev. No:2 Date: 19.12.2025`) should not be used as `drawing_number`. Comparing manual extractions against the existing Anthropic-run outputs for the DEICO sample set showed the model treating this same recurring footer stamp three different ways across sibling drawings (null, used as drawing_number, and "unclear, not used"), so the ambiguity was real rather than a one-off.

### Changed

- Raised the Anthropic extractor `max_tokens` from `8192` to `16384` to reduce how often full-page technical drawings with large tables hit the output limit in the first place.
- Updated `docs/schema.md`'s table guidance, which still said to avoid `columns` plus positional `values` with no exception. Clarified that this rule is about what the extractor (model) produces; the final product JSON may still show the collapsed `columns`/`values` shape when the validator has proven every row's columns are identical, per `docs/extraction.md`.

## 2026-07-08

### Added

- Allowlisted the current incoming DEICO PDF sample set so another contributor can use the same one-time source inputs without opening `inputs/incoming/` to future files by default.
- Added an `--ollama-think` CLI option for passing Ollama's thinking setting to local full-page, crop, and OCR-target extraction calls.
- Updated README and pipeline examples to use separate experiment output roots so model tests do not overwrite existing outputs.

## 2026-07-01

### Added

- Created `AGENTS.md` as project memory for future human contributors and AI agents.
- Documented the initial technical drawing parser direction.
- Defined the core evidence-preservation principle: extracted values must remain traceable to original document coordinates and source regions.
- Documented the expected pipeline stages: ingestion, page normalization, layout detection, region cropping, OCR and vision extraction, semantic normalization, validation, and output.
- Added an initial extensible region type vocabulary for technical drawing segmentation.
- Added initial TODO items for schema design, folder structure, ingestion, PDF handling, OCR, layout detection, sample JSON output, and validation.
- Created this `CHANGELOG.md` to track project decisions and implementation order.
- Added the initial project folder structure for docs, inputs, outputs, samples, source code, and tests.
- Added `docs/pipeline.md` with the planned CLI-oriented batch processing flow and registry behavior.
- Added `docs/schema.md` with the first result JSON and region metadata draft.
- Updated `README.md` with the current project status and key locations.
- Documented the processing registry rule: use SHA-256 fingerprints to skip already completed files.
- Added a minimal Python package with a CLI entry point.
- Added `tdp process` / `python -m technical_drawing_parser process` for batch processing.
- Added `tdp status` / `python -m technical_drawing_parser status` for registry summaries.
- Added `tdp.py` as a local no-install CLI wrapper.
- Improved skip output to show the existing result path and run id when a file was already processed.
- Improved CLI help text with usage examples and documented the `process` command.
- Documented the recommended onboarding reading order for future agents.
- Added input discovery for PDF, PNG, JPG, JPEG, TIFF, and TIF files.
- Added SHA-256 fingerprinting and `outputs/index.json` registry handling.
- Added initial run output generation with copied input, `manifest.json`, `result.json`, `warnings.json`, and full-page region metadata.
- Simplified the MVP output flow to write one product JSON per input under `outputs/products/` instead of per-run output directories.
- Simplified product JSON to user-facing technical fields and moved developer metadata to `outputs/internal/`.
- Added VLM extraction documentation, a canonical prompt builder, and per-file prompt output under `outputs/internal/`.
- Shortened generated output names by removing common filename noise and preferring brand/code style slugs.
- Clarified the current MVP limitations and updated project TODOs toward VLM extraction.
- Added `.env.example`, local `.env` loading, and default no-cost `none` extractor configuration.
- Added `environment.yml` and documented Conda as the recommended setup path.
- Documented local Ollama/VLM test results and added Python package metadata ignores.
- Added an opt-in Ollama extractor with raw response capture and product JSON validation.
- Marked completed extractor calls with invalid product JSON as `validation_failed` in internal metadata.
- Documented model trial results: `gemma4:cloud` is the best current extractor, `minicpm-v4.6` is the local baseline, and several local Qwen/Gemma models crash on the current machine.
- Added `size` to the documented product JSON shape so sheet size is not confused with drawing scale.
- Clarified that `AGENTS.md` is the single onboarding entry point for future agents.
- Added basic JPG and PNG image size detection using the Python standard library.
- Added standard-library unit tests for input discovery and registry skip behavior.
- Added `.gitignore` rules for Python cache files and generated runtime outputs.
- Added product JSON normalization for common VLM output issues: string nulls, empty scalar values, sheet size values placed in `scale`, dimension type aliases, missing dimension fields, and mojibake diameter symbols.
- Updated the VLM prompt to distinguish drawing sheet `size` from drawing `scale`.
- Added first-page PDF rendering through PyMuPDF and routed PDF VLM extraction through the rendered PNG page image.
- Recorded rendered PDF page metadata in internal outputs and documented the new `outputs/internal/page_images/` location.
- Changed registry behavior so failed files are retried by default while completed matching fingerprints are still skipped.
- Added a validator warning for suspicious `#` symbols in diameter dimensions while preserving the original `raw_text`.
- Extended PDF rendering to write every page image and record page-level full-page regions while keeping one product JSON per input.
- Added internal page-level VLM extraction records for rendered PDF pages while keeping the product JSON based on page 1 until merge behavior is implemented.
- Increased PDF rendering to 300 DPI for better small text visibility.
- Added opt-in overlapping page tile generation with `--generate-crops` and internal tile metadata for future crop extraction and dedupe.
- Documented the crop dedupe direction: use page-space tile coordinates as the primary signal and optional VLM position hints as supporting evidence.
- Added opt-in crop VLM extraction with `--extract-crops`; tile results are stored in internal `tile_extractions` and are not merged into product JSON yet.
- Added internal `tile_extraction_summary` duplicate-candidate reporting for crop dimensions using normalized values and overlapping tile bboxes.
- Added full-page-supported versus tile-only classification to `tile_extraction_summary` to prepare for safer crop merge behavior.
- Added a compact `<name>.tile_summary.json` review artifact with strong/weak duplicate and tile-only classifications.
- Added optional local OCR with RapidOCR via `--ocr`, storing coordinate-aware raw OCR blocks and filtered numeric OCR candidates internally.
- Added `--ocr-engine rapidocr` so future OCR engines can be compared behind the same internal OCR schema.
- Added `--generate-ocr-target-crops` for confidence-driven OCR target crops around high-confidence numeric candidates missed by full-page extraction.
- Kept OCR target selection general by filtering only weak single-number fragments while leaving semantic crop classification to future refinement; OCR/full-page comparison still uses loose matching keys for quantity prefixes and diameter symbols without changing extracted text.
- Added opt-in OCR target VLM refinement with `--refine-ocr-targets`, storing crop classifications and structured refinement JSON internally without merging into product JSON.
- Added an internal OCR target refinement summary with classification counts and review-only product dimension merge candidates.
- Added `dimension_tables` to the product schema and prompt so tabular measurements can be extracted with row and column context instead of being ignored or flattened into ambiguous dimensions.
- Updated OCR target refinement summaries to distinguish new dimension candidates from values already covered by flat dimensions or dimension tables.
- Added metadata review candidates to OCR target refinement summaries so OCR-target metadata can flag supported, conflicting, or missing product metadata without automatic correction.
- Added compact review JSON artifacts under `outputs/internal/reviews/` for quick inspection without reading the full internal audit JSON.
- Simplified review JSON coverage to counts only so compact reviews stay focused on actionable issues.
- Clarified prompts so single-letter symbolic references are not extracted as dimensions unless a numeric value is visible with the reference.
- Added `sheet` to the product schema for title-block sheet information such as `1/1`.
- Added a general `tables` field for non-dimensional tables such as pinout, connection, specification, note, or legend tables.
- Added compact OCR refinement review decision buckets: `merge_ready` for high-confidence uncovered candidates and `needs_review` for uncertain candidates or metadata issues.
- Added OCR target visual text verification fields so crop refinements can report the VLM-read `visual_text` and whether it supports the OCR hint.
- Tightened VLM prompts to preserve visible metadata formatting, avoid assigning isolated numbers to metadata, and treat OCR target text strictly as a hint.
- Tightened `merge_ready` review decisions so pattern-like dimensions and OCR/visual text conflicts remain in `needs_review`.
- Added safe metadata merge from OCR-target refinement for empty product metadata fields only; existing product values are never overwritten automatically.
- Added OCR-target local context and visible label evidence so crop refinements can distinguish labeled metadata, tables, dimensions, notes, and isolated numbers without full-page context.
- Added a narrow evidence-based scale ratio punctuation correction for cases where OCR-target refinement supports `2:1` but the full-page value was decimalized as `2.1`.
- Added `brand_name` to the product schema so company, manufacturer, brand, or logo text can be kept separate from product names, drawing numbers, and document names.
- Tightened metadata prompts so source filenames are not copied into product, document, or drawing-number fields unless visibly printed in the drawing.
- Tightened unit extraction prompts so units are not inferred from drawing style, decimal formatting, product type, or previous drawings.
- Added an opt-in Anthropic Claude extractor for full-page VLM extraction through the Messages API.

### Changed

- Simplified OCR CLI behavior so `--ocr` now runs the OCR-assisted pipeline: local OCR, missed-value candidate detection, target crop generation, VLM target refinement when an extractor is enabled, and compact review output.
- Removed the separate `--generate-ocr-target-crops` and `--refine-ocr-targets` commands from the active CLI surface.
- Paused OCR-target metadata merge into product JSON; refinement evidence remains internal, but product JSON now reflects the full-page VLM result unless merge behavior is deliberately re-enabled.
- Made OCR target refinement use the active VLM extractor so `--ocr` works with Anthropic as well as Ollama.
- Changed product table output toward readable row `cells` with explicit `column` and `value` pairs, while normalizing older `columns`/`values` responses into the new shape.
- Tightened unit prompts so global dimension units apply only to physical product dimensions and not to unrelated table/specification values.
- Preserved visible decimal separators in dimension values while normalizing common unit spellings such as `millimetres` to `mm`.
- Added filename-like metadata warnings for product, document, and drawing-number fields without automatically rewriting the extractor output.
- Removed the product-level unit field from the schema; units now live on individual dimensions while global unit notes remain in `notes`.

### Notes

- The initial reference sample is `DEICO_DE8135_Technical_Drawing_page-0001.jpg`.
- The sample shows that the parser must support mixed technical drawings, including product views, PCB land patterns, mounting details, schematic diagrams, dimensions, notes, and title blocks.
