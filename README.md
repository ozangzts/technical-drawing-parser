# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a minimal CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes traceable outputs under `outputs/runs/`.

## Usage

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

## Key Locations

- `AGENTS.md`: project memory and rules for future AI agents
- `CHANGELOG.md`: project change history
- `docs/pipeline.md`: planned processing flow
- `docs/schema.md`: initial JSON schema draft
- `inputs/incoming/`: place source drawings here
- `outputs/runs/`: processing outputs will be written here
