"""Command-line interface for processing drawings and checking registry status."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_EXTRACTOR, load_dotenv, read_config
from .ocr import DEFAULT_OCR_ENGINE, SUPPORTED_OCR_ENGINES
from .pipeline import process_inputs


def build_parser() -> argparse.ArgumentParser:
    config = read_config()
    parser = argparse.ArgumentParser(
        prog="tdp",
        description="Process technical drawings into traceable JSON outputs.",
        epilog=(
            "Examples:\n"
            "  python tdp.py process\n"
            "  python tdp.py process inputs/incoming\n"
            "  python tdp.py process --extractor none\n"
            "  python tdp.py process --extractor ollama --model gemma4:cloud\n"
            "  python tdp.py process inputs/incoming/DEICO_DE3000_Technical_Drawing.pdf --extractor ollama --model minicpm-v4.6 --outputs outputs_ollama_de3000_minicpm_test --force\n"
            "  python tdp.py process inputs/incoming/DEICO_DE3000_Technical_Drawing.pdf --extractor ollama --model qwen3-vl:2b --ollama-think true --outputs outputs_ollama_de3000_qwen3vl_think_test --force\n"
            "  python tdp.py process --extractor anthropic --model <claude-model> --outputs outputs_claude_test --force\n"
            "  python tdp.py process --extractor ollama --model gemma4:cloud --ocr --force\n"
            "  python tdp.py process --extractor anthropic --model <claude-model> --outputs outputs_claude_test --ocr --force\n"
            "  python tdp.py process --generate-crops\n"
            "  python tdp.py process --extractor ollama --model moondream --extract-crops --force\n"
            "  python tdp.py process path/to/drawing.jpg --force\n"
            "  python tdp.py status"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser(
        "process",
        help="Process drawings from an input file or directory.",
        description=(
            "Process new technical drawing files. Files with completed matching "
            "SHA-256 fingerprints are skipped unless --force is used."
        ),
    )
    process_parser.add_argument(
        "input_path",
        nargs="?",
        default="inputs/incoming",
        help="Input file or directory. Defaults to inputs/incoming.",
    )
    process_parser.add_argument(
        "--outputs",
        default="outputs",
        help="Output root directory. Defaults to outputs.",
    )
    process_parser.add_argument(
        "--force",
        action="store_true",
        help="Process files even if the same content was already completed.",
    )
    process_parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Compatibility option; failed files are retried by default.",
    )
    process_parser.add_argument(
        "--generate-crops",
        action="store_true",
        help="Generate overlapping page tiles under outputs/internal/crops.",
    )
    process_parser.add_argument(
        "--ocr",
        action="store_true",
        help=(
            "Run the OCR-assisted pipeline: local OCR, missed-value candidates, "
            "target crops, VLM target refinement when an extractor is enabled, "
            "and compact review output."
        ),
    )
    process_parser.add_argument(
        "--ocr-engine",
        default=DEFAULT_OCR_ENGINE,
        choices=sorted(SUPPORTED_OCR_ENGINES),
        help="OCR engine to use when --ocr is enabled. Defaults to rapidocr.",
    )
    process_parser.add_argument(
        "--extract-crops",
        action="store_true",
        help="Run opt-in VLM extraction for generated crops and store internal tile_extractions.",
    )
    process_parser.add_argument(
        "--extractor",
        default=config.extractor,
        choices=[DEFAULT_EXTRACTOR, "ollama", "anthropic"],
        help="Extraction provider to use. Defaults to TDP_EXTRACTOR or none.",
    )
    process_parser.add_argument(
        "--model",
        default=config.model,
        help="Model name for future extractor providers. Defaults to TDP_MODEL.",
    )
    process_parser.add_argument(
        "--ollama-think",
        choices=["true", "false", "low", "medium", "high", "max"],
        help=(
            "Optional Ollama thinking setting. Use true/false for models that "
            "support toggling, or low/medium/high/max for models with thinking levels."
        ),
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Show registry status.",
        description="Show the current processing registry summary.",
    )
    status_parser.add_argument(
        "--outputs",
        default="outputs",
        help="Output root directory. Defaults to outputs.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "process"):
        input_path = Path(getattr(args, "input_path", "inputs/incoming"))
        outputs_root = Path(getattr(args, "outputs", "outputs"))
        summary = process_inputs(
            input_path=input_path,
            outputs_root=outputs_root,
            force=getattr(args, "force", False),
            retry_failed=getattr(args, "retry_failed", False),
            extractor=getattr(args, "extractor", DEFAULT_EXTRACTOR),
            model=getattr(args, "model", None),
            ollama_think=normalize_ollama_think(
                getattr(args, "ollama_think", None)
            ),
            generate_crops=getattr(args, "generate_crops", False),
            extract_crops=getattr(args, "extract_crops", False),
            run_ocr=getattr(args, "ocr", False),
            ocr_engine=getattr(args, "ocr_engine", DEFAULT_OCR_ENGINE),
        )
        print_summary(summary)
        return 0 if summary["failed"] == 0 else 1

    if args.command == "status":
        from .registry import load_registry

        registry = load_registry(Path(args.outputs) / "index.json")
        entries = registry.get("files", [])
        completed = sum(1 for entry in entries if entry.get("status") == "completed")
        failed = sum(1 for entry in entries if entry.get("status") == "failed")
        print(f"Registry: {Path(args.outputs) / 'index.json'}")
        print(f"Total entries: {len(entries)}")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        return 0

    parser.print_help()
    return 1


def normalize_ollama_think(value: str | None) -> bool | str | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def print_summary(summary: dict[str, int | list[str]]) -> None:
    print(f"Found {summary['found']} file(s).")
    print(f"Processed {summary['processed']} new file(s).")
    print(f"Skipped {summary['skipped']} already processed file(s).")
    print(f"Failed {summary['failed']} file(s).")

    messages = summary.get("messages", [])
    if messages:
        print()
        for message in messages:
            print(message)
