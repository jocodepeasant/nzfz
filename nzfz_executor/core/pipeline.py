"""执行管线：串联动作分发、条件评估与重试机制，顺序执行一组动作。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nzfz_executor.actions.base import ActionResult
from nzfz_executor.context import ExecutionContext

if TYPE_CHECKING:
    from nzfz_executor.actions.base import ActionRegistry
    from nzfz_executor.events import EventBus
    from nzfz_executor.core.dispatcher import ActionDispatcher


class ExecutionPipeline:
    """执行管线：按顺序执行一组动作，支持条件评估与重试。"""

    def __init__(
        self,
        dispatcher: ActionDispatcher,
        condition_evaluator: Any,
        retry_manager: Any,
        event_bus: EventBus,
    ) -> None:
        """初始化执行管线。

        Args:
            dispatcher: 动作分发器，负责将动作分发到对应处理器。
            condition_evaluator: 条件评估器，判断动作前置条件是否满足。
            retry_manager: 重试管理器，处理动作执行失败后的重试逻辑。
            event_bus: 事件总线，用于管线执行过程中的事件通知。
        """
        self._dispatcher = dispatcher
        self._condition_evaluator = condition_evaluator
        self._retry_manager = retry_manager
        self._event_bus = event_bus

    def run(self, actions: list[dict[str, Any]], context: ExecutionContext) -> list[ActionResult]:
        """顺序执行一组动作，返回每个动作的执行结果。

        Args:
            actions: 动作数据列表，每个元素为动作类型及参数的字典。
            context: 执行上下文，提供运行时信息。

        Returns:
            list[ActionResult]: 所有动作的执行结果列表。

        Raises:
            NotImplementedError: 子类或后续实现需覆盖此方法。
        """
        raise NotImplementedError