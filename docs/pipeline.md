# Pipeline

This document describes the processing flow for technical drawings. Keep it simple and update it as implementation decisions change.

## Input Location

Place source files in:

```text
inputs/incoming/
```

Supported formats are expected to include PDF, PNG, JPG, JPEG, and TIFF. The parser should not modify or move files from `inputs/incoming/` by default.

## Product Output Location

Each processed input gets one product JSON file:

```text
outputs/products/<input_or_product_code>.json
```

At the current MVP stage, the output name is derived from the input filename and cleaned to prefer a short brand/code style name when possible. For example, `DEICO_DE8135_Technical_Drawing_page-0001.jpg` becomes `deico_de8135.json`. Later, once title block extraction exists, the output name can use a detected product or drawing code.

Product JSON includes flat `dimensions` for direct drawing callouts, `dimension_tables` for tabular measurements where row and column context is required to understand values, and `tables` for non-dimensional tables such as pinout, connection, specification, note, or legend tables.

Developer-facing metadata is written separately:

```text
outputs/internal/<input_or_product_code>.internal.json
outputs/internal/<input_or_product_code>.vlm_prompt.txt
outputs/internal/<input_or_product_code>.tile_summary.json
outputs/internal/reviews/<input_or_product_code>.review.json
outputs/internal/<input_or_product_code>.raw_response.txt
outputs/internal/<input_or_product_code>_page_002.raw_response.txt
outputs/internal/tile_responses/<input_or_product_code>_page_001_tile_001.raw_response.txt
```

Additional debug artifacts and crops should only be added when they become necessary.

`<input_or_product_code>.review.json` is a compact human-facing review artifact. It summarizes extraction status, counts, validation warnings, and actionable OCR refinement decisions without requiring readers to open the full internal audit JSON. Detailed covered candidates remain in the full internal JSON.

When `--generate-crops` is used, overlapping page tiles are written under:

```text
outputs/internal/crops/<name>_page_001_tile_001.png
```

Tile crops are evidence/debug artifacts and do not change the product JSON. Each tile keeps the original page-space bbox, source page, crop path, tile size, and overlap pixels so later crop extraction can be deduplicated against page coordinates.

When `--extract-crops` is used with `--extractor ollama`, crops are generated if needed and each tile is extracted into internal `tile_extractions`. Tile extraction does not merge into the product JSON yet.

Internal output also includes `tile_extraction_summary`, which counts tile dimensions, reports duplicate candidate groups using normalized dimension values and overlapping source tile bboxes, and classifies tile dimensions as full-page-supported or tile-only candidates.

The same summary is also written to `<input_or_product_code>.tile_summary.json` so candidate review does not require reading the full internal JSON.

PDF inputs are rendered at 300 DPI to page PNGs under:

```text
outputs/internal/page_images/<name>_page_001.png
outputs/internal/page_images/<name>_page_002.png
```

The original PDF remains the source document. Rendered page images are recorded in internal metadata. When VLM extraction is enabled, each rendered page is extracted and stored in `page_extractions`. The current product JSON still uses page 1 until merge behavior is implemented, so multi-page PDFs get a product warning.

When `--ocr` is used, the selected local OCR engine runs on page images and writes coordinate-aware `raw_ocr_blocks` plus filtered numeric `ocr_candidates` into internal metadata. OCR candidates are cross-checked against full-page VLM dimensions when VLM extraction is enabled. The initial supported engine is `rapidocr`.

When `--ocr` is used with a VLM extractor, high-confidence OCR candidates that were not found in the full-page extraction are written as padded target crops under:

```text
outputs/internal/ocr_target_crops/<name>_page_001_ocr_target_001.png
```

These crops are targeted evidence/refinement inputs only. They do not change product JSON, and only very weak single-number OCR fragments are filtered out before target crop generation. OCR/full-page comparison uses loose matching keys for quantity prefixes and diameter symbols, but extracted text is preserved as read. Semantic decisions such as whether a crop is a dimension, scale, title-block value, or unrelated metadata should be left to a later refinement step instead of hard-coded into target selection.

The same `--ocr` run sends each target crop to the VLM with a focused refinement prompt. Results are stored in internal `ocr_target_refinements` and raw responses are written under:

```text
outputs/internal/ocr_target_responses/<name>_page_001_ocr_target_001.raw_response.txt
```

OCR target refinement classifies each crop as `dimension`, `metadata`, `note`, `uncertain`, or `irrelevant`. The OCR text is treated as a hint only: the VLM should re-read the visible crop text, return `visual_text`, and set `ocr_text_supported` to indicate whether the crop visually supports the OCR hint. It should also return local crop evidence such as `local_context` and `visible_label` so isolated numbers can be separated from labeled title-block values, tables, notes, or real dimension callouts.

When `--ocr` is used without a VLM extractor, the pipeline stores OCR blocks and candidates but skips target crop refinement with a processing warning.

Internal output also includes `ocr_target_refinement_summary`, which counts refinement classifications and lists product-dimension `merge_candidates` for later review. Merge candidates are split into values already covered by flat `dimensions`, values already covered by `dimension_tables`, and truly new `new_dimension_candidates`.

Metadata refinements are summarized as `metadata_review_candidates`. These compare OCR-target metadata values such as `scale`, `revision_date`, `size`, and `sheet` against the product JSON and mark them as `supported`, `conflict`, or `missing_in_product`.

Safe metadata merge is intentionally narrow and evidence-based. The pipeline may fill an empty product metadata field from OCR-target refinement only when the refinement is metadata, the product field is currently empty, confidence is high, the OCR hint is not visually rejected, `visual_text` matches the proposed value, local crop context supports metadata, and the field belongs to the product JSON metadata schema. Existing product values are never overwritten automatically.

Compact review JSON intentionally hides candidates that are already covered or merely supported. It exposes only actionable decision buckets:

- `applied_merges`: safe metadata values already filled into product JSON from OCR-target refinement.
- `merge_ready`: high-confidence OCR-target refinements that are not covered by full-page extraction, have clean OCR/visual text support, and use a safe dimension type for a future merge step.
- `needs_review`: low-confidence candidates, metadata conflicts, or metadata missing from product JSON.

## Processing Registry

The parser should maintain a registry at:

```text
outputs/index.json
```

The registry prevents repeated work. On each run, the parser should scan `inputs/incoming/`, compute a content fingerprint for each file, and skip files that already have a completed registry entry with the same fingerprint.

Use SHA-256 for the content fingerprint unless there is a strong reason to change it.

Default behavior:

- Same file content already completed: skip.
- Same filename with changed content: create or overwrite the product JSON.
- Previous failed run without a completed entry: process again.
- `--force`: reprocess even if the file was already completed.
- `--retry-failed`: kept as a compatibility option; failed files are retried by default.

## CLI Commands

Use the local CLI wrapper:

```bash
python tdp.py --help
python tdp.py process
python tdp.py process --extractor none
python tdp.py process --extractor ollama --model gemma4:cloud --force
python tdp.py process --extractor ollama --model gemma4:cloud --ocr --force
python tdp.py process --generate-crops
python tdp.py process --extractor ollama --model gemma4:cloud --extract-crops --force
python tdp.py status
```

`process` is the command that starts drawing processing. Command names keep the CLI extensible as future actions are added.

## Configuration

Copy `.env.example` to `.env` for local settings. The default configuration is:

```text
TDP_EXTRACTOR=none
TDP_MODEL=
```

`none` does not call any external API. Future VLM providers can use the same configuration pattern.

## Current Minimal Pipeline Stages

1. Discover input files.
2. Compute file metadata and SHA-256 fingerprint.
3. Check `outputs/index.json`.
4. Read basic file and image metadata.
5. Render every page when the input is a PDF.
6. Create initial page and full-page region records.
7. Write one simple product JSON file under `outputs/products/`.
8. Write internal metadata under `outputs/internal/`.
9. Write the VLM extraction prompt under `outputs/internal/`.
10. For PDF inputs with VLM extraction enabled, extract each rendered page into internal `page_extractions`.
11. Optionally run the OCR-assisted pipeline when `--ocr` is used.
12. Write coordinate-aware `raw_ocr_blocks` and `ocr_candidates`.
13. When a VLM extractor is enabled, generate OCR-driven target crops and refine them into internal `ocr_target_refinements`.
14. Optionally generate overlapping page tiles when `--generate-crops` or `--extract-crops` is used.
15. Optionally extract generated tiles into internal `tile_extractions` when `--extract-crops` and a VLM extractor are enabled.
16. Update `outputs/index.json`.

Later stages will add page-level merge behavior, safe OCR-target merge behavior, layout detection, crop extraction merge behavior, debug overlays, and region-specific semantic extraction.

## Crop And Dedupe Direction

The initial crop strategy is deterministic overlapping tiles, not whitespace-based segmentation. Whitespace can carry visual relationships in technical drawings, such as leader lines, dimension arrows, table boundaries, and schematic connections.

Default crop settings:

- Tile size: 1024 px
- Overlap: 25 percent
- Minimum edge tile: 384 px

Current crop extraction keeps tile results internal until merge behavior is proven. Duplicate candidates can be detected with:

- same page
- same normalized text, value, type, or label
- overlapping or neighboring source tile bboxes
- optional VLM position hints such as `left_edge`, `right_edge`, `top_edge`, `bottom_edge`, `center`, or `unknown`

Position hints should be treated as supporting evidence only. Page-space tile coordinates are the primary deterministic dedupe signal.

Before any product merge, tile dimensions should be compared with full-page extraction:

- `full_page_supported_candidates`: tile dimensions that match full-page dimensions by page, value, type, and non-conflicting label or quantity.
- `tile_only_candidates`: tile dimensions not seen in full-page extraction. These may be new useful evidence or crop-only false positives.
- `duplicate_candidate_groups`: tile dimensions that look repeated across overlapping source tiles.

Duplicate groups are classified as `strong_duplicate` when label/quantity evidence is strong enough, otherwise `weak_duplicate`. Tile-only candidates are classified as `tile_only_candidate`, `weak_tile_only`, or `non_product_candidate` to make manual review smaller and safer.

## Traceability

Every output must remain traceable to:

- original input path
- input fingerprint
- page number
- source coordinates when available
- region id when available
