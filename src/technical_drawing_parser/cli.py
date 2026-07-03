"""Command-line interface for processing drawings and checking registry status."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_EXTRACTOR, load_dotenv, read_config
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
            "  python tdp.py process --generate-crops\n"
            "  python tdp.py process --extractor ollama --model moondream --force\n"
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
        "--extractor",
        default=config.extractor,
        choices=[DEFAULT_EXTRACTOR, "ollama"],
        help="Extraction provider to use. Defaults to TDP_EXTRACTOR or none.",
    )
    process_parser.add_argument(
        "--model",
        default=config.model,
        help="Model name for future extractor providers. Defaults to TDP_MODEL.",
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
            generate_crops=getattr(args, "generate_crops", False),
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
