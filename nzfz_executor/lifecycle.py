"""生命周期管理：管理执行器的状态转换（IDLE / RUNNING / PAUSED / STOPPED）。"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nzfz_executor.events import EventBus

logger = logging.getLogger(__name__)


class LifecycleState(Enum):
    """执行器生命周期状态。"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class LifecycleManager:
    """生命周期管理器：控制执行器的状态转换，并通过事件总线通知。"""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._state = LifecycleState.IDLE
        self._event_bus = event_bus

    @property
    def state(self) -> LifecycleState:
        """当前生命周期状态。"""
        return self._state

    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._state == LifecycleState.RUNNING

    @property
    def is_paused(self) -> bool:
        """是否已暂停。"""
        return self._state == LifecycleState.PAUSED

    def start(self) -> None:
        """启动执行：IDLE / STOPPED → RUNNING。"""
        if self._state not in (LifecycleState.IDLE, LifecycleState.STOPPED):
            logger.warning("无法从 %s 状态启动", self._state.value)
            return
        self._transition(LifecycleState.RUNNING)

    def pause(self) -> None:
        """暂停执行：RUNNING → PAUSED。"""
        if self._state != LifecycleState.RUNNING:
            logger.warning("无法从 %s 状态暂停", self._state.value)
            return
        self._transition(LifecycleState.PAUSED)

    def resume(self) -> None:
        """恢复执行：PAUSED → RUNNING。"""
        if self._state != LifecycleState.PAUSED:
            logger.warning("无法从 %s 状态恢复", self._state.value)
            return
        self._transition(LifecycleState.RUNNING)

    def stop(self) -> None:
        """停止执行：RUNNING / PAUSED → STOPPED。"""
        if self._state == LifecycleState.IDLE:
            logger.warning("无法从 IDLE 状态停止")
            return
        self._transition(LifecycleState.STOPPED)

    def reset(self) -> None:
        """重置为空闲状态：→ IDLE。"""
        self._transition(LifecycleState.IDLE)

    def _transition(self, new_state: LifecycleState) -> None:
        """执行状态转换并通知事件总线。"""
        old_state = self._state
        self._state = new_state
        logger.info("生命周期状态转换: %s → %s", old_state.value, new_state.value)
        if self._event_bus is not None:
            self._event_bus.emit("lifecycle_change", {
                "old_state": old_state.value,
                "new_state": new_state.value,
            })