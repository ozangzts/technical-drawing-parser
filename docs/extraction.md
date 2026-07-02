# Extraction

The project goal is simple:

```text
technical drawing -> visible product information -> simple product JSON
```

## Strategy

Use a vision-language model as the main extractor. OCR can be added later as a supporting signal, but OCR alone is not enough for technical drawings because dimensions, arrows, regions, schematic diagrams, and land patterns need visual interpretation.

## Rules For Extraction

- Extract only information visible in the drawing.
- Do not guess missing values.
- Preserve original numeric formatting, decimal separators, symbols, and quantity markers in `raw_text`.
- Use `null` when a field is not visible.
- Use empty arrays when no values are visible.
- Add warnings for unclear, ambiguous, cropped, or unreadable information.
- Keep the product JSON readable for a non-developer.
- Store developer/debug details separately under `outputs/internal/`.

## Product JSON Shape

```json
{
  "source_file": "drawing.jpg",
  "product_name": null,
  "document_name": null,
  "drawing_number": null,
  "revision": null,
  "revision_date": null,
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

## VLM Prompt

The canonical prompt lives in `src/technical_drawing_parser/extraction/prompt.py`.

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
- `qwen2.5vl:3b` crashed on `ollama run` with `llama-server process has terminated: exit status 0xe06d7363`.
- The development machine has 8 GB RAM and a GTX 1050, so larger local VLMs may be slow or unstable.

Recommended next local steps:

1. Use the `ollama` extractor as an explicit opt-in provider.
2. Start with `moondream` because it runs on the current machine.
3. Keep `none` as the default extractor.
4. Store local model name, raw response, and extraction status in internal metadata.
5. If local quality is insufficient, compare with hosted providers such as Groq or Gemini later.

Example:

```bash
python tdp.py process --extractor ollama --model moondream --force
```

Do not assume OCR is enough for this project. Technical drawing dimensions require visual context, so OCR should remain optional support unless testing proves otherwise.
