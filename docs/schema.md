# Schema Draft

This document sketches the first JSON output shape. It is intentionally small and should evolve with real samples.

## Result JSON

`result.json` should contain normalized extraction data plus evidence references.

```json
{
  "schema_version": "0.1.0",
  "document": {
    "original_filename": "drawing.pdf",
    "fingerprint": "sha256:...",
    "page_count": 1,
    "units": null
  },
  "title_block": {
    "product_name": null,
    "document_name": null,
    "drawing_number": null,
    "revision": null,
    "revision_date": null,
    "scale": null,
    "sheet": null
  },
  "dimensions": [],
  "notes": [],
  "regions": [],
  "raw_ocr_blocks": [],
  "uncertain_fields": []
}
```

## Region Object

```json
{
  "id": "page_001_region_001",
  "type": "full_page",
  "page": 1,
  "bbox": {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0
  },
  "source_ref": "input/drawing.pdf#page=1",
  "crop_ref": null,
  "confidence": 1.0
}
```

## Uncertain Field Object

```json
{
  "field": "material",
  "value": null,
  "reason": "No material callout was detected.",
  "evidence": [],
  "confidence": 0.0
}
```

## Design Notes

- Keep normalized fields stable and readable.
- Do not discard raw OCR or region metadata.
- Add new sections only when a real drawing needs them.
- Preserve original text where normalization may lose important context.

