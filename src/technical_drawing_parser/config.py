from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXTRACTOR = "none"


@dataclass(frozen=True)
class AppConfig:
    extractor: str = DEFAULT_EXTRACTOR
    model: str | None = None


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_config() -> AppConfig:
    extractor = os.getenv("TDP_EXTRACTOR", DEFAULT_EXTRACTOR).strip().lower() or DEFAULT_EXTRACTOR
    model = os.getenv("TDP_MODEL", "").strip() or None
    return AppConfig(extractor=extractor, model=model)

