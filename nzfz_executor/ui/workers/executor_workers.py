"""执行器 UI Worker：在后台线程运行占位执行任务（P2-05）。"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal, Slot

from nzfz_executor.core.models import ConnectedWindow
from nzfz_executor.ui.workers.stop_token import StopToken

EXECUTOR_PLACEHOLDER_TOTAL_STEPS = 20
EXECUTOR_PLACEHOLDER_STEP_SLEEP_S = 0.2


class ExecutorWorker(QObject):
    """后台执行一次占位任务，用于验证异步执行与协作停止。"""

    completed = Signal(int)
    stopped = Signal(int)
    failed = Signal(int, str)
    log = Signal(int, str)
    progress = Signal(int, int, str)

    def __init__(
        self,
        execution_id: int,
        context: ConnectedWindow | None,
        stop_token: StopToken,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._execution_id = execution_id
        self._context = context
        self._stop_token = stop_token

    @Slot()
    def run(self) -> None:
        try:
            if self._context is None:
                self.failed.emit(
                    self._execution_id,
                    "当前未连接游戏窗口，无法执行任务",
                )
                return

            self.log.emit(self._execution_id, "执行任务已启动")

            total_steps = EXECUTOR_PLACEHOLDER_TOTAL_STEPS

            for step in range(total_steps):
                if self._stop_token.is_stop_requested():
                    self.log.emit(self._execution_id, "任务收到停止请求")
                    self.stopped.emit(self._execution_id)
                    return

                percent = int((step + 1) / total_steps * 100)
                self.progress.emit(
                    self._execution_id,
                    percent,
                    f"正在执行占位步骤 {step + 1}/{total_steps}",
                )

                time.sleep(EXECUTOR_PLACEHOLDER_STEP_SLEEP_S)

            self.log.emit(self._execution_id, "执行任务已完成")
            self.completed.emit(self._execution_id)

        except Exception as exc:
            self.failed.emit(self._execution_id, str(exc))
