# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes simple product JSON files under `outputs/products/`.

Opt-in VLM extraction through Ollama or Anthropic Claude is available for image and PDF inputs. PDF inputs are rendered to page PNG images; page-level extraction is stored internally, while the current product JSON uses the page 1 full-page VLM result until merge behavior is deliberately re-enabled. `--ocr` remains available for internal OCR-assisted evidence and review, but OCR refinement does not currently mutate product JSON.

## Usage

## Setup

Conda is the recommended setup path for this project.

Create the environment:

```bash
conda env create -f environment.yml
```

Activate it:

```bash
conda activate technical-drawing-parser
```

Update an existing environment after dependencies change:

```bash
conda env update -f environment.yml --prune
```

Run tests:

```bash
python -m unittest discover -s tests
```

Optional local configuration:

```bash
copy .env.example .env
```

The default configuration uses `TDP_EXTRACTOR=none`, which does not call any external API.

Show available commands:

```bash
python tdp.py --help
```

If the package was installed from `environment.yml`, this also works:

```bash
tdp --help
```

Process the default input directory:

```bash
python tdp.py process
```

Process with explicit defaults:

```bash
python tdp.py process --extractor none
```

Generate overlapping page crops for visual review:

```bash
python tdp.py process --generate-crops
```

Run full-page VLM extraction only:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --outputs outputs_ollama_gemma4_cloud_test --force
```

Test one local Ollama model on one PDF without overwriting existing outputs:

```bash
python tdp.py process inputs/incoming/DEICO_DE3000_Technical_Drawing.pdf --extractor ollama --model minicpm-v4.6 --outputs outputs_ollama_de3000_minicpm_test --force
```

For Ollama thinking-capable models, pass `--ollama-think`. The output root is created automatically:

```bash
python tdp.py process inputs/incoming/DEICO_DE3000_Technical_Drawing.pdf --extractor ollama --model qwen3-vl:2b --ollama-think true --outputs outputs_ollama_de3000_qwen3vl_think_test --force
```

Some Ollama models support thinking levels:

```bash
python tdp.py process inputs/incoming/DEICO_DE3000_Technical_Drawing.pdf --extractor ollama --model gpt-oss --ollama-think medium --outputs outputs_ollama_de3000_gpt_oss_medium_test --force
```

Run a Claude full-page extraction test into a separate output root:

```bash
python tdp.py process --extractor anthropic --model <claude-model> --outputs outputs_claude_test --force
```

Hosted vision models can be costly on full-page 300 DPI technical drawings. Use a single file, a separate output root, and a cheaper model first when experimenting. The committed `outputs_claude_sonnet_test/` folder preserves one Sonnet comparison run for the current sample PDFs.

Run OCR-assisted VLM refinement and compact review output:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --ocr --force
```

The same OCR-assisted flow can use Claude:

```bash
python tdp.py process --extractor anthropic --model <claude-model> --outputs outputs_claude_test --ocr --force
```

Use a new `--outputs` folder for each experiment, such as `outputs_ollama_de3000_minicpm_test` or `outputs_ollama_de3000_qwen3vl_think_test`, to keep previous runs intact.

Choose a supported OCR engine when needed:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --ocr --ocr-engine rapidocr --force
```

Extract generated crops into internal metadata without merging them into the product JSON:

```bash
python tdp.py process --extractor ollama --model gemma4:cloud --extract-crops --force
```

Process a specific file or directory:

```bash
python tdp.py process inputs/incoming
```

Show registry status:

```bash
python tdp.py status
```

`process` is the command that starts drawing processing. The CLI uses command names because later actions can live under the same `tdp.py` entry point without changing the basic usage pattern.

## Key Locations

- `AGENTS.md`: project memory and rules for future AI agents
- `CHANGELOG.md`: project change history
- `docs/pipeline.md`: planned processing flow
- `docs/schema.md`: initial JSON schema draft
- `inputs/incoming/`: place source drawings here
- `outputs/products/`: product JSON outputs will be written here
- `outputs/internal/`: developer-facing metadata will be written here
- `outputs/internal/reviews/`: compact review summaries for quick inspection
- `.env.example`: local configuration template
