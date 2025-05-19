import json
from pathlib import Path
from typing import Any, Optional

def load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupted/empty → treat as missing
        return None

def save_json(path: Path, data: Any) -> None:
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
