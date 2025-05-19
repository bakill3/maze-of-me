"""
Minimal JSON helpers shared by the OAuth collectors and CLI.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Return dict from <path> or {} if the file is missing / invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict | list | Any) -> None:
    """Write *data* as pretty-printed UTF-8 JSON to <path>."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
