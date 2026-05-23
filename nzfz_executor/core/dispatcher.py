"""动作分发器：根据动作类型将动作数据分发到对应的处理器执行。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.actions.base import ActionRegistry, ActionResult
from nzfz_executor.context import ExecutionContext


class ActionDispatcher:
    """动作分发器：根据动作类型查找注册的处理器并执行动作。"""

    def __init__(self, action_registry: type[ActionRegistry] = ActionRegistry) -> None:
        self._registry = action_registry

    def dispatch(self, action_data: dict[str, Any], context: ExecutionContext) -> ActionResult:
        action_type = action_data.get("type", "")
        handler = self._registry.get(action_type)
        if handler is None:
            return ActionResult(
                success=False,
                error=f"未知动作类型: {action_type or '(空)'}",
            )
        context.action_data = action_data
        return handler.execute(context)
