# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a minimal CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes simple product JSON files under `outputs/products/`.

Opt-in VLM extraction through Ollama is available for image inputs. PDF inputs are rendered to page PNG images; page-level extraction is stored internally, while the current product JSON uses page 1 until merge behavior is implemented.

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

Run local OCR for coordinate-aware text evidence:

```bash
python tdp.py process --ocr --ocr-engine rapidocr
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
- `.env.example`: local configuration template
