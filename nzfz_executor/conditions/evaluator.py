"""条件求值器：根据条件配置和执行上下文，调度注册表中的处理器完成条件判断。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.conditions.base import ConditionRegistry
from nzfz_executor.context import ExecutionContext


class ConditionEvaluator:
    """条件求值器：接收条件配置字典，依次调用对应处理器进行求值。"""

    def __init__(self, registry: ConditionRegistry) -> None:
        self._registry = registry

    def evaluate(self, conditions: dict[str, Any], context: ExecutionContext) -> bool:
        if not conditions:
            return True
        for condition_type, value in conditions.items():
            handler = self._registry.get(condition_type)
            if handler is None:
                return False
            if not handler.evaluate(value, context):
                return False
        return True
