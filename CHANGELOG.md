# Changelog

All notable changes to this project should be documented in this file.

The format is inspired by Keep a Changelog, and this project uses chronological entries while the project is still in early exploration.

## 2026-07-01

### Added

- Created `AGENTS.md` as project memory for future human contributors and AI agents.
- Documented the initial technical drawing parser direction.
- Defined the core evidence-preservation principle: extracted values must remain traceable to original document coordinates and source regions.
- Documented the expected pipeline stages: ingestion, page normalization, layout detection, region cropping, OCR and vision extraction, semantic normalization, validation, and output.
- Added an initial extensible region type vocabulary for technical drawing segmentation.
- Added initial TODO items for schema design, folder structure, ingestion, PDF handling, OCR, layout detection, sample JSON output, and validation.
- Created this `CHANGELOG.md` to track project decisions and implementation order.
- Added the initial project folder structure for docs, inputs, outputs, samples, source code, and tests.
- Added `docs/pipeline.md` with the planned CLI-oriented batch processing flow and registry behavior.
- Added `docs/schema.md` with the first result JSON and region metadata draft.
- Updated `README.md` with the current project status and key locations.
- Documented the processing registry rule: use SHA-256 fingerprints to skip already completed files.
- Added a minimal Python package with a CLI entry point.
- Added `tdp process` / `python -m technical_drawing_parser process` for batch processing.
- Added `tdp status` / `python -m technical_drawing_parser status` for registry summaries.
- Added `tdp.py` as a local no-install CLI wrapper.
- Improved skip output to show the existing result path and run id when a file was already processed.
- Improved CLI help text with usage examples and documented the `process` command.
- Documented the recommended onboarding reading order for future agents.
- Added input discovery for PDF, PNG, JPG, JPEG, TIFF, and TIF files.
- Added SHA-256 fingerprinting and `outputs/index.json` registry handling.
- Added initial run output generation with copied input, `manifest.json`, `result.json`, `warnings.json`, and full-page region metadata.
- Added basic JPG and PNG image size detection using the Python standard library.
- Added standard-library unit tests for input discovery and registry skip behavior.
- Added `.gitignore` rules for Python cache files and generated runtime outputs.

### Notes

- The initial reference sample is `DEICO_DE8135_Technical_Drawing_page-0001.jpg`.
- The sample shows that the parser must support mixed technical drawings, including product views, PCB land patterns, mounting details, schematic diagrams, dimensions, notes, and title blocks.
