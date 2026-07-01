# Pipeline

This document describes the processing flow for technical drawings. Keep it simple and update it as implementation decisions change.

## Input Location

Place source files in:

```text
inputs/incoming/
```

Supported formats are expected to include PDF, PNG, JPG, JPEG, and TIFF. The parser should not modify or move files from `inputs/incoming/` by default.

## Run Output Location

Each processed input gets its own run directory:

```text
outputs/runs/<run_id>/
```

The current run directory structure is:

```text
outputs/runs/<run_id>/
  input/
  pages/
  crops/
  debug/
  ocr/
  regions/
  manifest.json
  result.json
  warnings.json
```

## Processing Registry

The parser should maintain a registry at:

```text
outputs/index.json
```

The registry prevents repeated work. On each run, the parser should scan `inputs/incoming/`, compute a content fingerprint for each file, and skip files that already have a completed registry entry with the same fingerprint.

Use SHA-256 for the content fingerprint unless there is a strong reason to change it.

Default behavior:

- Same file content already completed: skip.
- Same filename with changed content: create a new run.
- Previous failed run: skip by default until retry behavior is implemented.
- `--force`: reprocess even if the file was already completed.
- `--retry-failed`: reprocess previously failed files.

## Current Minimal Pipeline Stages

1. Discover input files.
2. Compute file metadata and SHA-256 fingerprint.
3. Check `outputs/index.json`.
4. Create a unique run directory for new work.
5. Copy the original input into the run directory.
6. Read basic file and image metadata.
7. Create initial page and full-page region records.
8. Write `manifest.json`.
9. Write `result.json`.
10. Update `outputs/index.json`.

Later stages will add PDF rendering, OCR, layout detection, crops, debug overlays, and semantic extraction.

## Traceability

Every output must remain traceable to:

- original input path
- input fingerprint
- run id
- page number
- source coordinates when available
- region id when available
