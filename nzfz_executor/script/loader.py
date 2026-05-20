"""脚本加载器模块，负责从文件或文本中加载脚本数据。"""

from pathlib import Path
from typing import Any


class ScriptLoader:
    """脚本加载器，用于从文件路径或原始文本中解析脚本内容并返回结构化数据。"""

    def load(self, path: Path) -> dict[str, Any]:
        """从指定文件路径加载脚本，返回解析后的字典数据。

        Args:
            path: 脚本文件路径

        Returns:
            解析后的脚本数据字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError

    def load_text(self, text: str) -> dict[str, Any]:
        """从原始文本字符串加载脚本，返回解析后的字典数据。

        Args:
            text: 脚本文本内容

        Returns:
            解析后的脚本数据字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError