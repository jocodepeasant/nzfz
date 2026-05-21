"""脚本校验器模块，负责对脚本数据进行格式与规则校验。"""

from pathlib import Path
from typing import Any


class ScriptValidator:
    """脚本校验器，用于校验脚本数据是否符合预定义的 Schema 规范。"""

    def __init__(self, schema_path: Path | None = None) -> None:
        """初始化脚本校验器。

        Args:
            schema_path: 校验规则文件路径，为 None 时使用内置默认规则
        """
        self.schema_path: Path | None = schema_path
        """校验规则文件路径"""

    def validate(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """校验脚本数据，返回错误列表。

        Args:
            data: 待校验的脚本数据字典

        Returns:
            错误信息列表，每项为包含错误详情的字典；无错误时返回空列表

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError

    def assert_valid(self, data: dict[str, Any]) -> None:
        """断言脚本数据合法，校验失败时抛出异常。

        Args:
            data: 待校验的脚本数据字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError