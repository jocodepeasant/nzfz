"""条件求值器：根据条件配置和执行上下文，调度注册表中的处理器完成条件判断。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.conditions.base import ConditionRegistry
from nzfz_executor.context import ExecutionContext


class ConditionEvaluator:
    """条件求值器：接收条件配置字典，依次调用对应处理器进行求值。"""

    def __init__(self, registry: ConditionRegistry) -> None:
        self._registry: ConditionRegistry = registry
        """条件处理器注册表，用于查找条件类型对应的处理器。"""

    def evaluate(self, conditions: dict[str, Any], context: ExecutionContext) -> bool:
        """对一组条件进行求值，所有条件均满足时返回 True。

        Args:
            conditions: 条件配置字典，键为条件类型，值为该条件的配置值。
            context: 当前执行上下文，提供运行时信息。

        Returns:
            所有条件均满足时返回 True，否则返回 False。
        """
        raise NotImplementedError