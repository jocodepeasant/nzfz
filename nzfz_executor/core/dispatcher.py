"""动作分发器：根据动作类型将动作数据分发到对应的处理器执行。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nzfz_executor.actions.base import ActionResult
from nzfz_executor.context import ExecutionContext

if TYPE_CHECKING:
    from nzfz_executor.actions.base import ActionRegistry


class ActionDispatcher:
    """动作分发器：根据动作类型查找注册的处理器并执行动作。"""

    def __init__(self, action_registry: ActionRegistry) -> None:
        """初始化动作分发器。

        Args:
            action_registry: 动作注册表，提供动作类型到处理器的映射。
        """
        self._registry = action_registry

    def dispatch(self, action_data: dict[str, Any], context: ExecutionContext) -> ActionResult:
        """分发动作到对应的处理器执行。

        Args:
            action_data: 动作数据字典，包含动作类型及参数。
            context: 执行上下文，提供运行时信息。

        Returns:
            ActionResult: 动作执行结果。

        Raises:
            NotImplementedError: 子类或后续实现需覆盖此方法。
        """
        raise NotImplementedError