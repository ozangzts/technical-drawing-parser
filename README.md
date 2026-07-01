# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a minimal CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes simple product JSON files under `outputs/products/`.

Semantic extraction is not implemented yet. The next major step is connecting a vision-language model so product names, drawing metadata, dimensions, tolerances, and notes can be extracted from the drawing image.

## Usage

Show available commands:

```bash
python tdp.py --help
```

Process the default input directory:

```bash
python tdp.py process
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
