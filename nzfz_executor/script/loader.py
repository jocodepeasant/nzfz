"""脚本加载器模块，负责从文件或文本中加载脚本数据。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nzfz_executor.errors import ScriptLoadError


class ScriptLoader:
    """脚本加载器，用于从文件路径或原始文本中解析脚本内容并返回结构化数据。"""

    def load(self, path: Path) -> dict[str, Any]:
        """从指定文件路径加载脚本，返回解析后的字典数据。"""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ScriptLoadError(str(path), str(exc)) from exc
        return self.load_text(text, source=str(path.resolve()))

    def load_text(self, text: str, *, source: str = "") -> dict[str, Any]:
        """从原始文本字符串加载脚本，返回解析后的字典数据。"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ScriptLoadError(source, str(exc)) from exc
        if not isinstance(data, dict):
            raise ScriptLoadError(source, "脚本根节点必须是 JSON 对象")
        return data
