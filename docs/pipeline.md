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

Developer-facing metadata is written separately:

```text
outputs/internal/<input_or_product_code>.internal.json
outputs/internal/<input_or_product_code>.vlm_prompt.txt
```

Additional debug artifacts and crops should only be added when they become necessary.

PDF inputs are rendered to a first-page PNG under:

```text
outputs/internal/page_images/<name>_page_001.png
```

The original PDF remains the source document. The rendered page image is used as the VLM image input and is recorded in internal metadata.

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
- Previous failed run: skip by default until retry behavior is implemented.
- `--force`: reprocess even if the file was already completed.
- `--retry-failed`: reprocess previously failed files.

## CLI Commands

Use the local CLI wrapper:

```bash
python tdp.py --help
python tdp.py process
python tdp.py process --extractor none
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
5. Render the first page when the input is a PDF.
6. Create initial page and full-page region records.
7. Write one simple product JSON file under `outputs/products/`.
8. Write internal metadata under `outputs/internal/`.
9. Write the VLM extraction prompt under `outputs/internal/`.
10. Update `outputs/index.json`.

Later stages will add multi-page PDF handling, OCR, layout detection, crops, debug overlays, and region-specific semantic extraction.

## Traceability

Every output must remain traceable to:

- original input path
- input fingerprint
- page number
- source coordinates when available
- region id when available
