"""动作处理器基类与注册机制：定义动作执行结果、抽象处理器接口及全局注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from nzfz_executor.context import ExecutionContext


@dataclass
class ActionResult:
    """动作执行结果：封装单个动作执行后的状态与返回数据。"""

    success: bool
    """动作是否执行成功"""

    skipped: bool = False
    """动作是否被跳过（例如条件不满足时）"""

    attempts: int = 1
    """执行尝试次数"""

    data: Any = None
    """动作执行返回的附加数据"""

    error: str | None = None
    """执行失败时的错误信息"""


class ActionHandler(ABC):
    """动作处理器抽象基类：所有具体动作处理器必须继承此类并实现 execute 方法。"""

    action_type: str = ""
    """动作类型标识符，子类必须覆写为唯一字符串"""

    @abstractmethod
    def execute(self, context: ExecutionContext) -> ActionResult:
        """执行动作。

        Args:
            context: 执行上下文，提供运行时所需信息。

        Returns:
            动作执行结果。

        Raises:
            NotImplementedError: 子类未实现时抛出。
        """
        raise NotImplementedError

    def validate(self, action_data: dict) -> list[str]:
        """校验动作数据是否合法。

        Args:
            action_data: 待校验的动作数据字典。

        Returns:
            校验错误信息列表，空列表表示校验通过。
        """
        return []


class ActionRegistry:
    """动作注册表：管理动作类型与对应处理器类的映射关系。"""

    _handlers: dict[str, type[ActionHandler]] = {}
    """已注册的动作处理器映射表，键为动作类型，值为处理器类"""

    @classmethod
    def register(cls, handler_class: type[ActionHandler]) -> None:
        """注册一个动作处理器类。

        Args:
            handler_class: 需要注册的动作处理器类，必须具有 action_type 属性。
        """
        cls._handlers[handler_class.action_type] = handler_class

    @classmethod
    def get(cls, action_type: str) -> ActionHandler | None:
        """根据动作类型获取对应的处理器实例。

        Args:
            action_type: 动作类型标识符。

        Returns:
            处理器实例，若未注册则返回 None。
        """
        handler_class = cls._handlers.get(action_type)
        if handler_class is not None:
            return handler_class()
        return None

    @classmethod
    def list_types(cls) -> list[str]:
        """获取所有已注册的动作类型标识符。

        Returns:
            已注册动作类型列表。
        """
        return list(cls._handlers.keys())