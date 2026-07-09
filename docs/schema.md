# Schema Draft

This document sketches the first JSON output shape. It is intentionally small and should evolve with real samples.

## Result JSON

Product JSON files under `outputs/products/` are the user-facing extraction results. They should stay simple and readable.

```json
{
  "source_file": "drawing.pdf",
  "brand_name": null,
  "product_name": null,
  "document_name": null,
  "drawing_number": null,
  "revision": null,
  "revision_date": null,
  "sheet": null,
  "size": null,
  "scale": null,
  "dimensions": [],
  "dimension_tables": [],
  "tables": [],
  "schematics": [],
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
- Keep `brand_name`, `product_name`, `drawing_number`, and `document_name` separate: company/logo text belongs in `brand_name`, human-readable product descriptions in `product_name`, short drawing/model/part codes in `drawing_number`, and document type text in `document_name`.
- Do not put developer/debug fields in product JSON.
- Store raw OCR, region metadata, fingerprints, and evidence details in internal JSON when needed.
- Add new sections only when a real drawing needs them.
- Preserve original text where normalization may lose important context.
- Preserve visible decimal separators in numeric strings. For example, if the drawing says `44,12`, keep `value` as `44,12` instead of converting it to `44.12`.
- Do not include a product-level unit field. Put units on each extracted dimension and keep global unit notes, such as "all dimensions are in millimeters", in `notes`.
- Normalize common unit spellings in unit fields when safe, such as `millimeters` or `millimetres` to `mm`.
- Use `dimension_tables` for tabular product measurements where row and column context is needed to understand values.
- Use `tables` for non-dimensional tables such as pinout, connection, specification, note, or legend tables.
- The extractor (model) always produces rows with readable `cells`, for example `{"column": "Signal", "value": "GND"}`, not disconnected `columns` plus positional `values` — this is what avoids positional-matching bugs where a model-produced row has the wrong number or order of values.
- The final product JSON may still show a table as a table-level `columns` header plus per-row `values`. The validator collapses to that shape only after parsing, and only when every row's `cells` provably share the exact same column sequence; an irregular table keeps the explicit `cells` shape. See `docs/extraction.md` and `collapse_uniform_columns` in `validator.py`.
- For repeated side-by-side table blocks, prefer one logical item per row, such as one connector pin or one specification row, instead of one very wide row with repeated headers.
- Use `schematics` for circuit-level diagrams that show component reference designators (`R1`, `C3`, `U2`, ...) or a named electrical parameter repeated across the diagram (a turns ratio, a resistor value): `{"title", "context", "components": ["R1", ...], "parameters": [{"label", "value", "context"}]}`. A functional/block diagram with only boxes and arrows, no reference designators or values, does not get a `schematics` entry; describe it in `warnings` instead.
- See `docs/extraction.md` for VLM extraction rules and dimension object guidance.
