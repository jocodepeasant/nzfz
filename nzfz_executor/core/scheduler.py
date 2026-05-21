"""波次调度器：按波次顺序调度执行管线，驱动脚本逐波执行。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nzfz_executor.context import ExecutionContext

if TYPE_CHECKING:
    from nzfz_executor.events import EventBus
    from nzfz_executor.core.pipeline import ExecutionPipeline


class WaveScheduler:
    """波次调度器：管理波次的顺序调度，将每波动作交给执行管线执行。"""

    def __init__(self, pipeline: ExecutionPipeline, event_bus: EventBus) -> None:
        """初始化波次调度器。

        Args:
            pipeline: 执行管线，负责执行单波内的动作序列。
            event_bus: 事件总线，用于波次调度过程中的事件通知。
        """
        self._pipeline = pipeline
        self._event_bus = event_bus

    def schedule(self, waves: list[dict[str, Any]], context: ExecutionContext) -> None:
        """按顺序调度波次执行。

        Args:
            waves: 波次列表，每个元素包含该波次的动作序列及元数据。
            context: 执行上下文，提供运行时信息。

        Raises:
            NotImplementedError: 子类或后续实现需覆盖此方法。
        """
        raise NotImplementedError