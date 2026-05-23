"""条件处理器基类与注册机制：定义条件处理器的抽象接口和全局注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nzfz_executor.context import ExecutionContext


class ConditionHandler(ABC):
    """条件处理器抽象基类：所有条件处理器必须继承此类并实现 evaluate 方法。"""

    condition_type: str = ""

    @abstractmethod
    def evaluate(self, value: Any, context: ExecutionContext) -> bool:
        raise NotImplementedError


class ConditionRegistry:
    """条件处理器注册表：管理条件类型与处理器类之间的映射关系。"""

    def __init__(self) -> None:
        self._handlers: dict[str, type[ConditionHandler]] = {}

    def register(self, handler_class: type[ConditionHandler]) -> None:
        self._handlers[handler_class.condition_type] = handler_class

    def get(self, condition_type: str) -> ConditionHandler | None:
        handler_class = self._handlers.get(condition_type)
        if handler_class is not None:
            return handler_class()
        return None

    def list_types(self) -> list[str]:
        return list(self._handlers.keys())
