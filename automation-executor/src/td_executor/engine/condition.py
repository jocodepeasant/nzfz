"""动作前置条件判断引擎。"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from td_executor.state import GameState

logger = logging.getLogger(__name__)


class ConditionEngine:

    def __init__(self, state: GameState) -> None:
        self.state = state

    def eval_conditions(self, conditions: dict[str, Any]) -> bool:
        for cond_type, cond_value in conditions.items():
            if cond_type == "resource_gte":
                if (self.state.resource or 0) < cond_value:
                    return False
            elif cond_type == "slot_empty":
                if self.state.slot_occupied.get(cond_value, False) is not False:
                    return False
            elif cond_type == "slot_occupied":
                if self.state.slot_occupied.get(cond_value, False) is not True:
                    return False
            elif cond_type == "wave_gte":
                if (self.state.wave or 0) < cond_value:
                    return False
            elif cond_type == "trap_level_lt":
                trap_id = cond_value["trap_id"]
                level = cond_value["level"]
                if self.state.trap_levels.get(trap_id, 1) >= level:
                    return False
            else:
                logger.warning("未知条件类型: %s，视为通过", cond_type)
        return True

    def eval_condition_failed_policy(self, on_condition_failed: dict) -> str:
        return on_condition_failed.get("policy", "skip")

    def wait_for_condition(
        self,
        conditions: dict,
        on_condition_failed: dict,
        check_fn: Callable[[], None] | None = None,
        timeout_ms: int = 30000,
    ) -> bool:
        policy = self.eval_condition_failed_policy(on_condition_failed)
        if policy == "skip":
            return False
        if policy != "wait":
            return False
        deadline = time.monotonic() + timeout_ms / 1000.0
        while True:
            if check_fn is not None:
                check_fn()
            if self.eval_conditions(conditions):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(1.0)
