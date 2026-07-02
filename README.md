# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a minimal CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes simple product JSON files under `outputs/products/`.

Opt-in VLM extraction through Ollama is available for image inputs. PDF inputs are rendered to first-page PNG images before extraction; multi-page PDF handling is not implemented yet.

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
