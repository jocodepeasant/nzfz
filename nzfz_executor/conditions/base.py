"""条件处理器基类与注册机制：定义条件处理器的抽象接口和全局注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nzfz_executor.context import ExecutionContext


class ConditionHandler(ABC):
    """条件处理器抽象基类：所有条件处理器必须继承此类并实现 evaluate 方法。"""

    condition_type: str
    """条件类型标识符，用于在注册表中唯一标识该处理器。"""

    @abstractmethod
    def evaluate(self, value: Any, context: ExecutionContext) -> bool:
        """评估条件是否满足。

        Args:
            value: 条件的配置值，由脚本定义提供。
            context: 当前执行上下文，提供运行时信息。

        Returns:
            条件是否满足，满足返回 True，否则返回 False。
        """
        raise NotImplementedError


class ConditionRegistry:
    """条件处理器注册表：管理条件类型与处理器类之间的映射关系。"""

    def __init__(self) -> None:
        self._handlers: dict[str, type[ConditionHandler]] = {}
        """已注册的条件处理器映射表，键为条件类型，值为处理器类。"""

    def register(self, handler_class: type[ConditionHandler]) -> None:
        """注册一个条件处理器类。

        Args:
            handler_class: 要注册的条件处理器类，必须包含 condition_type 类属性。
        """
        pass

    def get(self, condition_type: str) -> ConditionHandler | None:
        """根据条件类型获取对应的处理器实例。

        Args:
            condition_type: 条件类型标识符。

        Returns:
            对应的处理器实例；若未注册则返回 None。
        """
        raise NotImplementedError

    def list_types(self) -> list[str]:
        """列出所有已注册的条件类型。

        Returns:
            已注册条件类型标识符的列表。
        """
        raise NotImplementedError