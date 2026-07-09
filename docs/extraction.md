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
- Put units on each extracted dimension. Do not include a product-level unit field. Keep global unit notes, such as "all dimensions are in millimeters", in `notes`.
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
- A table row `label` that only restates the row's first `cells` value (for example `label: "Pin 1"` next to `{"column": "Pin Number", "value": "1"}`) is dropped to `null`. The information is not lost, since it still lives in `cells`; only the redundant echo is removed. A `label` that carries information beyond the first cell, such as `"2.1 Storage Temperature"` next to `{"column": "Parameter", "value": "Storage Temperature"}`, is kept.
- When a table has at least two rows and every row's `cells` share the exact same column sequence (same names, same order, same count), the table collapses to a table-level `columns` header plus per-row `values` (dropping the repeated column names from every row). This is verified after parsing, not assumed from the model's raw output, so a table with any row that has a different column set, order, or length keeps the explicit `cells` shape instead — nothing is ever positionally guessed. If every row's `label` is also null after the label-redundancy rule above, `label` is dropped too and each row becomes a plain `values` array; if any row's `label` carries real information, rows keep the `{"label": ..., "values": [...]}` shape. See `collapse_uniform_columns` in `validator.py`.
- OCR-target refinement is currently review/evidence only. Safe metadata merge helper code exists, but product JSON mutation from OCR refinement is paused unless the pipeline design changes deliberately.

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

`label` and `context` answer different questions and neither should repeat `raw_text` or `value`: `label` is a short, reusable category for *what kind* of measurement this is (`hole diameter`, `overall width`, `pin pitch`); `context` is *where* this specific instance is (`recommended land pattern`, `front view`, `connector body`), so it is not confused with another dimension of the same category elsewhere on the sheet. Real Anthropic-run output across the DEICO sample set showed this was not consistently followed: `label` was left `null` for every dimension on some drawings, populated with an invented category on others, and on one drawing (`DE4001`) set to `"R10"` — a plain echo of `raw_text`, adding nothing. The validator now nulls out a `label` that exactly matches `raw_text` or `value` (`drop_label_redundant_with_dimension_value` in `validator.py`) as a safety net, but the real fix is the clearer prompt rule, since a model that already decided to repeat the value isn't corrected by that decision being explained better after the fact.

Allowed initial `type` values:

- `linear`
- `diameter`
- `radius`
- `angle`
- `thread`
- `pattern`
- `unknown`

`pattern` is for a repeated center-to-center spacing or pitch (a pin pitch, a hole pitch), especially one marked with a repeat count like `(x6)`. `linear` is for a single, non-repeated straight-line measurement (an overall length, width, or height), even if it also carries a quantity marker. This distinction is called out explicitly in the prompt because comparing manual extractions against the existing Anthropic-run outputs showed the model choosing `pattern` for a pitch dimension on one sample and `linear` for the same kind of pitch dimension on a sibling sample — the validator's `pitch -> pattern` alias (see below) only fixes this when the model's own `type` string is literally `pitch`, not when it directly guesses `linear`.

## VLM Prompts

The canonical prompt builders live in `src/technical_drawing_parser/extraction/prompt.py`:

- `build_vlm_prompt`: full-page extraction.
- `build_tile_vlm_prompt`: overlapping tile extraction.
- `build_ocr_target_refinement_prompt`: OCR-target crop refinement.

`build_vlm_prompt` and `build_tile_vlm_prompt` share most of their rules (unit inference limits, metadata field distinctions, table formatting, etc.) since a crop is extracting from the same kind of drawing, just a smaller visible area. The rule text that is identical between the two lives once as a named `RULE_*` constant near the top of `prompt.py` and is referenced by both builders, instead of being retyped in each function. Only genuinely crop-specific lines (the crop framing sentence, the cropped/incomplete warning, wording that mentions "this crop") stay local to `build_tile_vlm_prompt`. This is a code-duplication fix, not a wording change: the rendered prompt text is unchanged from before the constants existed.

The pipeline writes the prompt used for each file to:

```text
outputs/internal/<name>.vlm_prompt.txt
```

This keeps the current MVP provider-independent while making the next VLM integration step explicit.

## Product JSON Formatting

`outputs/products/*.json` is written with `src/technical_drawing_parser/json_format.py` instead of plain `json.dump(indent=2)`. Standard `indent=2` puts every dict key on its own line, so a table with many short, uniform rows (one pin per row, one connector per row) turns into hundreds of lines for a handful of short values.

`format_json_compact` renders the same data, choosing per node whether it fits on one line (up to `DEFAULT_MAX_LINE_LENGTH`, currently 200 characters) before falling back to the normal expanded form. A short row such as a pinout entry collapses to one line; a row containing a long specification paragraph still expands so nothing is cut off. This is formatting only — the underlying values, key order, and structure are unchanged, so `json.loads` on the compact output equals `json.loads` on the equivalent `indent=2` output. Internal/debug JSON (`outputs/internal/*.json`, the registry, tile summaries, reviews) still uses plain `indent=2` through `write_json(..., compact=False)`, since verbosity matters less there than in the product JSON a human is expected to read.

## Truncated Response Detection

Large tables or long specification text can push a full-page response past the model's output token limit before the JSON object closes. If the response is cut off exactly after a nested closing brace, the truncated text can still parse as syntactically valid JSON while silently missing every field that comes after the cut point (for example later tables, `notes`, or `warnings`), and nothing in the shape check would otherwise catch this.

To avoid a truncated response being reported as a clean `completed` result:

- The Anthropic extractor checks the response `stop_reason`; `max_tokens` marks the response as truncated.
- The Ollama extractor checks the response `done_reason`; `length` marks the response as truncated.
- When an extraction is marked truncated, the pipeline appends an explicit warning to both the internal `validation_warnings` and the parsed product JSON `warnings`, and forces the extraction status to `validation_failed` even if the response otherwise parsed without other warnings.
- The Anthropic extractor requests `max_tokens: 16384` (raised from the original `8192`) to reduce how often full-page technical drawings hit the limit in the first place. Requesting a higher `max_tokens` does not cost more unless the model actually generates that many tokens.

This is a reliability safeguard, not an extraction-quality improvement: it does not recover the missing data, it only turns a silent partial result into a visible one so a retry (for example with a still-higher `max_tokens`) can be made deliberately instead of the gap going unnoticed.

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
3. Use the `anthropic` extractor for small hosted API comparisons when an Anthropic API key is available. Claude Sonnet produced the strongest sample outputs so far, but full-page 300 DPI drawings were expensive; keep future hosted tests small unless budget is approved.
4. Keep `none` as the default extractor.
5. Store local/cloud model name, raw response, and extraction status in internal metadata.
6. Improve schema/prompt/validator around `size` versus `scale`, string `"null"`, empty strings, and allowed dimension types.
7. If full-page extraction quality is insufficient, move to title-block and region crop extraction.

Example:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --force
python tdp.py process --extractor anthropic --model <claude-model> --outputs outputs_claude_test --force
```

Do not assume OCR is enough for this project. Technical drawing dimensions require visual context, so OCR should remain optional support unless testing proves otherwise.

Committed Claude Sonnet comparison outputs for the current sample PDFs are stored in `outputs_claude_sonnet_test/`.

## Unit And Table Extraction Rules

- Use explicit units only. A global note such as "all dimensions are in millimeters" may support physical product dimensions, but it must not be applied to pin numbers, connector labels, table indexes, dates, scale values, revision values, voltage, current, temperature, humidity, frequency, standards, or free-text notes.
- Preserve visible numeric formatting in `raw_text` and `value`. Do not convert decimal commas to decimal points just for normalization.
- Normalize common unit spellings in unit fields when safe, such as `millimeters`, `millimetres`, or `millimeter` to `mm`.
- Keep table output readable for humans. Product JSON should use row `cells` with explicit `column` and `value` pairs instead of disconnected `columns` plus positional `values`.
- When a visible table repeats the same headers across side-by-side blocks, normalize it into logical rows where possible, such as one connector pin or one specification per row.

## Drawing Number Vs. Form Control Stamp

Across the DEICO sample set, no title block has ever had a field literally labeled "Drawing Number." Two different kinds of codes can look like a candidate for `drawing_number`, and they should be told apart:

- A short product/model code, such as `DE4001`, that identifies this specific product. It usually appears inside `product_name` (`"DE3000 - Battery Simulation Unit ..."`) or `document_name` (`"DE4001 - Technical Drawing"`) rather than in its own field. Extract it into `drawing_number` anyway, even though it is embedded in another field's text.
- A generic document/form control stamp, such as `SBL-0033 Rev. No:2 Date: 19.12.2025`, printed in a sheet border. It carries its own revision and date that are unrelated to the title block's `revision`/`revision_date`, because it identifies the drawing *template* or company form, not this specific product. Do not use it as `drawing_number`; keep it in `notes`.

Comparing manual extractions against the existing Anthropic-run outputs for this sample set showed the model treating the same recurring form-control stamp three different ways across sibling drawings (left null, used as `drawing_number`, and "unclear, not used") — this distinction was added to the prompt specifically because that inconsistency was real, not a one-off misread.

## Schematic Vs. Block Diagram

A drawing can show two visually similar but functionally different kinds of diagram, and only one of them gets a `schematics` entry:

- A **circuit-level schematic** shows component reference designators (`R1`, `C3`, `U2`, ...) and/or a named electrical parameter repeated across the diagram (a transformer turns ratio, a resistor value, an impedance). Extract these into `schematics`: `components` as the flat list of visible reference designators, `parameters` as label/value pairs for the repeated values. In the DEICO sample set, the same bus-coupler network (a `BUS` line with resistor/transformer stub taps, each transformer at a `1:1,41` turns ratio) appears at three different stub counts (`DE8133`: 3 stubs, `R1`-`R8`; `DE8135`: 5 stubs, `R1`-`R12`; `DE8207`: 7 stubs, `R1`-`R14`) — structuring it means the repeated ratio and the component count can be checked for consistency across the family instead of only existing as three separately worded warning sentences.
- A **functional/block diagram** shows only boxes and arrows describing a flow (`USB -> Controller -> I2C/GPIO`), with no reference designators and no electrical values. This does not get a `schematics` entry — there is nothing extractable beyond the box labels, which are already just short text. Describe it in `warnings` instead, as with `DE3000`'s "System Functionality Chart" and `DE4001`'s "Circuitry" block diagram.

Do not force an empty or placeholder `schematics` entry onto a block diagram just because it looks diagram-shaped; the field should only ever contain diagrams that actually had extractable component/parameter data.

When the same parameter value repeats identically across a diagram's repeating units (the same `1:1,41` turns ratio on every stub tap), list it once in `parameters` with a context noting that it applies to each unit, rather than one identical entry per unit. This was not originally specified: a blind test session (a fresh Claude Code session with no memory of this project's conventions, given only the rendered prompt text and the image, asked to answer in one shot) independently produced one repeated entry per stub instead, which is not wrong but is more verbose than needed.
