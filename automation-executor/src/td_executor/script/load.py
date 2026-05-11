"""Load script JSON from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_script_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "脚本根节点必须是 JSON object"
        raise ValueError(msg)
    return data
