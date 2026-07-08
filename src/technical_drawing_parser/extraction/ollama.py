"""Opt-in local VLM extraction through the Ollama HTTP API."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OLLAMA_MODEL = "moondream"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


@dataclass(frozen=True)
class ExtractionResponse:
    status: str
    raw_response: str | None
    error: str | None = None


def extract_with_ollama(
    image_path: Path,
    prompt: str,
    model: str | None,
    think: bool | str | None = None,
    url: str = DEFAULT_OLLAMA_URL,
) -> ExtractionResponse:
    payload = {
        "model": model or DEFAULT_OLLAMA_MODEL,
        "prompt": prompt,
        "images": [encode_image(image_path)],
        "stream": False,
        "format": "json",
    }
    if think is not None:
        payload["think"] = think
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        return ExtractionResponse(status="failed", raw_response=None, error=str(error))

    raw_response = data.get("response")
    if not isinstance(raw_response, str):
        return ExtractionResponse(
            status="failed",
            raw_response=json.dumps(data, ensure_ascii=False),
            error="Ollama response did not include a string `response` field.",
        )

    return ExtractionResponse(status="completed", raw_response=raw_response)


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
