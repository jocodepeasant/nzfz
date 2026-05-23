"""波次调度器：按波次顺序调度执行管线，驱动脚本逐波执行。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.context import ExecutionContext
from nzfz_executor.core.pipeline import ExecutionPipeline
from nzfz_executor.events import EventBus


class WaveScheduler:
    """波次调度器：管理波次的顺序调度，将每波动作交给执行管线执行。"""

    def __init__(self, pipeline: ExecutionPipeline, event_bus: EventBus) -> None:
        self._pipeline = pipeline
        self._event_bus = event_bus

    def schedule(self, waves: list[dict[str, Any]], context: ExecutionContext) -> None:
        for wave_index, wave in enumerate(waves):
            wave_no = wave.get("wave", wave.get("wave_index", wave_index + 1))
            context.state.current_wave = wave_no
            actions = wave.get("actions") or []
            self._event_bus.emit("wave_start", {"wave_index": wave_no, "wave": wave})
            results = self._pipeline.run(actions, context)
            self._event_bus.emit(
                "wave_end",
                {"wave_index": wave_no, "wave": wave, "results": results},
            )
