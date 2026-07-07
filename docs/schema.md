# Schema Draft

This document sketches the first JSON output shape. It is intentionally small and should evolve with real samples.

## Result JSON

Product JSON files under `outputs/products/` are the user-facing extraction results. They should stay simple and readable.

```json
{
  "source_file": "drawing.pdf",
  "product_name": null,
  "document_name": null,
  "drawing_number": null,
  "revision": null,
  "revision_date": null,
  "sheet": null,
  "size": null,
  "scale": null,
  "units": null,
  "dimensions": [],
  "dimension_tables": [],
  "tables": [],
  "tolerances": [],
  "notes": [],
  "warnings": []
}
```

## Internal JSON

Developer-facing metadata should be written separately under `outputs/internal/`.

Internal JSON may include fingerprints, source paths, image metadata, regions, raw OCR blocks, and uncertainty details. These fields should not clutter the product JSON.

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
  "source_ref": "inputs/incoming/drawing.pdf#page=1",
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
- Do not put developer/debug fields in product JSON.
- Store raw OCR, region metadata, fingerprints, and evidence details in internal JSON when needed.
- Add new sections only when a real drawing needs them.
- Preserve original text where normalization may lose important context.
- Use `dimension_tables` for tabular product measurements where row and column context is needed to understand values.
- Use `tables` for non-dimensional tables such as pinout, connection, specification, note, or legend tables.
- See `docs/extraction.md` for VLM extraction rules and dimension object guidance.
