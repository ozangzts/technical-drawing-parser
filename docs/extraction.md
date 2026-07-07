# Extraction

The project goal is simple:

```text
technical drawing -> visible product information -> simple product JSON
```

## Strategy

Use a vision-language model as the main extractor. OCR is a supporting signal for coordinate-aware evidence and targeted refinement, but OCR alone is not enough for technical drawings because dimensions, arrows, regions, schematic diagrams, and land patterns need visual interpretation.

## Rules For Extraction

- Extract only information visible in the drawing.
- Do not guess missing values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in `raw_text`.
- Use `null` when a field is not visible.
- Use empty arrays when no values are visible.
- Add warnings for unclear, ambiguous, cropped, or unreadable information.
- Keep the product JSON readable for a non-developer.
- Store developer/debug details separately under `outputs/internal/`.

## Product JSON Normalization

Extractor output is normalized with narrow deterministic rules before it is written as product JSON:

- String placeholders such as `"null"`, empty strings, and `"N/A"` become JSON `null` for scalar fields.
- Sheet sizes such as `A3` and `A4` belong in `size`, not `scale`.
- Dimension objects are padded to the expected shape when fields are missing.
- Known dimension type aliases such as `hole diameter`, `pad diameter`, and `pitch` are mapped to allowed schema values.
- Unknown dimension types are set to `unknown` and recorded as warnings.
- Obvious mojibake for the diameter symbol is repaired.
- Suspicious but plausible symbol misreads, such as `#` in a diameter dimension, are recorded as warnings without changing `raw_text`.
- OCR-target refinement may safely fill empty product metadata fields when the crop provides high-confidence visual support. Existing product metadata is not overwritten, except for narrow scale-ratio punctuation correction backed by OCR-target evidence.

These rules clean schema shape and common formatting errors only. They should not infer values that are not visible in the drawing.

## Product JSON Shape

```json
{
  "source_file": "drawing.jpg",
  "brand_name": null,
  "product_name": null,
  "document_name": null,
  "drawing_number": null,
  "revision": null,
  "revision_date": null,
  "sheet": null,
  "size": null,
  "scale": null,
  "units": null,
  "dimensions": [
    {
      "raw_text": "61,3",
      "value": "61,3",
      "unit": "mm",
      "type": "linear",
      "quantity": null,
      "label": "overall length",
      "context": "top product view"
    }
  ],
  "dimension_tables": [],
  "tables": [],
  "tolerances": [],
  "notes": [],
  "warnings": []
}
```

## Dimension Object

Use this shape for visible dimensions:

```json
{
  "raw_text": "(x11) DIA 1,22 (HOLE DIAMETER)",
  "value": "1,22",
  "unit": "mm",
  "type": "diameter",
  "quantity": 11,
  "label": "hole diameter",
  "context": "recommended land pattern"
}
```

Allowed initial `type` values:

- `linear`
- `diameter`
- `radius`
- `angle`
- `thread`
- `pattern`
- `unknown`

## VLM Prompts

The canonical prompt builders live in `src/technical_drawing_parser/extraction/prompt.py`:

- `build_vlm_prompt`: full-page extraction.
- `build_tile_vlm_prompt`: overlapping tile extraction.
- `build_ocr_target_refinement_prompt`: OCR-target crop refinement.

The pipeline writes the prompt used for each file to:

```text
outputs/internal/<name>.vlm_prompt.txt
```

This keeps the current MVP provider-independent while making the next VLM integration step explicit.

## Local VLM Notes

Local VLM extraction is preferred before paid hosted APIs when practical.

Current local test context:

- Ollama is installed and `ollama --version` works.
- `llama3.2:1b` runs successfully in Ollama.
- `moondream` runs successfully in Ollama.
- The first `moondream` extractor pipeline call completed, but the response did not validate as product JSON. Treat `moondream` as a connectivity baseline, not a proven extraction-quality model.
- `minicpm-v4.6` runs locally and returns valid product JSON, but it made visible reading mistakes on the DEICO sample. Treat it as the current local baseline.
- `qwen2.5vl:3b` crashed on `ollama run` with `llama-server process has terminated: exit status 0xe06d7363`.
- `qwen3-vl:2b` crashed with the same `0xe06d7363` load failure on this Windows / GTX 1050 machine.
- Local `gemma4` variants also hit the same load failure on this machine.
- `gemma4:cloud` produced the best result so far for the DEICO sample: valid JSON, most key dimensions, title block information, and units. It still confused `size` and `scale`, so schema/prompt/validator improvements are needed.
- The development machine has 8 GB RAM and a GTX 1050, so larger local VLMs may be slow or unstable.

Recommended next local steps:

1. Use the `ollama` extractor as an explicit opt-in provider.
2. Use `gemma4:cloud` for quality checks when cloud use is acceptable.
3. Use `minicpm-v4.6` as the current local baseline when cloud use is not acceptable.
4. Keep `none` as the default extractor.
5. Store local/cloud model name, raw response, and extraction status in internal metadata.
6. Improve schema/prompt/validator around `size` versus `scale`, string `"null"`, empty strings, and allowed dimension types.
7. If full-page extraction quality is insufficient, move to title-block and region crop extraction.

Example:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --force
```

Do not assume OCR is enough for this project. Technical drawing dimensions require visual context, so OCR should remain optional support unless testing proves otherwise.
