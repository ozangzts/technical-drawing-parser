"""Human-friendlier JSON serialization for product output files.

Standard `json.dumps(indent=2)` puts every dict key on its own line, so a
table with many short, uniform rows (one pin, one connector, one
specification line) turns into hundreds of lines for a handful of values.
This renders the exact same data, just choosing per node whether it fits
comfortably on one line before falling back to the normal expanded form.
Nothing about the underlying values changes: this is formatting only.
"""

from __future__ import annotations

import json
from typing import Any

DEFAULT_MAX_LINE_LENGTH = 200


def format_json_compact(
    data: Any,
    indent: int = 2,
    max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
) -> str:
    return _render(data, indent, 0, max_line_length) + "\n"


def _render(value: Any, indent: int, depth: int, max_line_length: int) -> str:
    pad = " " * (indent * depth)

    if isinstance(value, (dict, list)):
        candidate = _inline(value)
        if len(pad) + len(candidate) <= max_line_length:
            return candidate

    if isinstance(value, dict):
        if not value:
            return "{}"
        inner_pad = " " * (indent * (depth + 1))
        items = [
            f"{inner_pad}{json.dumps(key)}: {_render(item, indent, depth + 1, max_line_length)}"
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"

    if isinstance(value, list):
        if not value:
            return "[]"
        inner_pad = " " * (indent * (depth + 1))
        items = [
            f"{inner_pad}{_render(item, indent, depth + 1, max_line_length)}"
            for item in value
        ]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"

    return json.dumps(value, ensure_ascii=False)


def _inline(value: Any) -> str:
    """Render `value` as tightly as possible on a single line."""
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{json.dumps(key)}: {_inline(item)}" for key, item in value.items()]
        return "{ " + ", ".join(items) + " }"

    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(_inline(item) for item in value) + "]"

    return json.dumps(value, ensure_ascii=False)
