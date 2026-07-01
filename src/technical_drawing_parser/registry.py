from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "0.1.0", "files": []}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_registry(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(registry, file, indent=2, ensure_ascii=False)
        file.write("\n")


def find_entries_by_fingerprint(
    registry: dict[str, Any],
    fingerprint: str,
) -> list[dict[str, Any]]:
    return [
        entry
        for entry in registry.get("files", [])
        if entry.get("fingerprint") == fingerprint
    ]


def should_process(
    registry: dict[str, Any],
    fingerprint: str,
    force: bool,
    retry_failed: bool,
) -> tuple[bool, str | None]:
    if force:
        return True, None

    entries = find_entries_by_fingerprint(registry, fingerprint)
    if any(entry.get("status") == "completed" for entry in entries):
        return False, "already completed"

    if entries and all(entry.get("status") == "failed" for entry in entries):
        if retry_failed:
            return True, None
        return False, "previously failed"

    return True, None


def find_latest_completed_entry(
    registry: dict[str, Any],
    fingerprint: str,
) -> dict[str, Any] | None:
    entries = [
        entry
        for entry in find_entries_by_fingerprint(registry, fingerprint)
        if entry.get("status") == "completed"
    ]
    if not entries:
        return None
    return entries[-1]


def append_registry_entry(registry: dict[str, Any], entry: dict[str, Any]) -> None:
    registry.setdefault("schema_version", "0.1.0")
    registry.setdefault("files", []).append(entry)
