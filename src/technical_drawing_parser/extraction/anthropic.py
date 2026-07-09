"""Opt-in VLM extraction through the Anthropic Messages API."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path

from .ollama import ExtractionResponse


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def extract_with_anthropic(
    image_path: Path,
    prompt: str,
    model: str | None,
    url: str = ANTHROPIC_API_URL,
) -> ExtractionResponse:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return ExtractionResponse(
            status="failed",
            raw_response=None,
            error="ANTHROPIC_API_KEY is not set.",
        )
    if not model:
        return ExtractionResponse(
            status="failed",
            raw_response=None,
            error="Anthropic extractor requires --model or TDP_MODEL.",
        )

    payload = {
        "model": model,
        "max_tokens": 16384,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type_for_image(image_path),
                            "data": encode_image(image_path),
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return ExtractionResponse(
            status="failed",
            raw_response=detail or None,
            error=f"HTTP {error.code}: {detail or error.reason}",
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        return ExtractionResponse(status="failed", raw_response=None, error=str(error))

    raw_response = extract_text_response(data)
    if raw_response is None:
        return ExtractionResponse(
            status="failed",
            raw_response=json.dumps(data, ensure_ascii=False),
            error="Anthropic response did not include a text content block.",
        )

    return ExtractionResponse(
        status="completed",
        raw_response=raw_response,
        truncated=response_was_truncated(data),
    )


def response_was_truncated(data: object) -> bool:
    return isinstance(data, dict) and data.get("stop_reason") == "max_tokens"


def extract_text_response(data: object) -> str | None:
    if not isinstance(data, dict):
        return None

    blocks = data.get("content")
    if not isinstance(blocks, list):
        return None

    texts = [
        block.get("text")
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    ]
    return "\n".join(texts).strip() or None


def media_type_for_image(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    if media_type in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        return media_type
    return "image/png"


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
