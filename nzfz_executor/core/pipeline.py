"""执行管线：串联动作分发、条件评估与重试机制，顺序执行一组动作。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.actions.base import ActionResult
from nzfz_executor.context import ExecutionContext
from nzfz_executor.core.dispatcher import ActionDispatcher
from nzfz_executor.events import EventBus


class ExecutionPipeline:
    """执行管线：按顺序执行一组动作，支持条件评估与重试。"""

    def __init__(
        self,
        dispatcher: ActionDispatcher,
        condition_evaluator: Any,
        retry_manager: Any,
        event_bus: EventBus,
    ) -> None:
        self._dispatcher = dispatcher
        self._condition_evaluator = condition_evaluator
        self._retry_manager = retry_manager
        self._event_bus = event_bus

    def run(self, actions: list[dict[str, Any]], context: ExecutionContext) -> list[ActionResult]:
        results: list[ActionResult] = []
        for action_data in actions:
            context.action_data = action_data
            conditions = action_data.get("conditions") or {}
            if not self._condition_evaluator.evaluate(conditions, context):
                result = ActionResult(
                    success=False,
                    skipped=True,
                    error="条件未满足",
                )
                results.append(result)
                self._event_bus.emit("action_completed", {"action": action_data, "result": result})
                continue

            result = self._dispatcher.dispatch(action_data, context)
            results.append(result)
            self._event_bus.emit("action_completed", {"action": action_data, "result": result})

            if not result.success:
                on_fail = action_data.get("on_fail") or {}
                if on_fail.get("policy") == "abort":
                    break
        return results
