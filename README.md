# technical-drawing-parser

Extract structured JSON from technical drawings while preserving source evidence, coordinates, and processing history.

## Current Status

This project has a minimal CLI-based batch processor that reads drawings from `inputs/incoming/`, skips files that were already processed, and writes product JSON files under `outputs/products/`.

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

`process` is the command that starts drawing processing. The CLI uses command names because later actions such as `status`, `inspect`, or `clean` can live under the same `tdp.py` entry point.

## Key Locations

- `AGENTS.md`: project memory and rules for future AI agents
- `CHANGELOG.md`: project change history
- `docs/pipeline.md`: planned processing flow
- `docs/schema.md`: initial JSON schema draft
- `inputs/incoming/`: place source drawings here
- `outputs/products/`: product JSON outputs will be written here
