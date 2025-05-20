# utils/json_io.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_json(fp: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(fp).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default

def save_json(fp: str | Path, obj: Any) -> None:
    Path(fp).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8"
    )
