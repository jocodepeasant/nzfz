"""执行器任务运行器：统一管理 ExecutorWorker 与 QThread 生命周期（P2-05）。"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Signal

from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.ui.workers.executor_workers import ExecutorWorker
from nzfz_executor.ui.workers.stop_token import StopToken

logger = logging.getLogger(__name__)


class ExecutorTaskRunner(QObject):
    """管理单次后台执行任务，同一时间只允许一个任务运行。"""

    completed = Signal(int)
    stopped = Signal(int)
    failed = Signal(int, str)
    log = Signal(int, str)
    progress = Signal(int, int, str)
    start_rejected = Signal(int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: ExecutorWorker | None = None
        self._stop_token: StopToken | None = None

    def start(
        self,
        execution_id: int,
        runtime_context: ExecutorRuntimeContext | None,
    ) -> bool:
        if self.is_running():
            message = "当前已有任务正在运行"
            logger.warning("Executor start rejected: %s", message)
            self.start_rejected.emit(execution_id, message)
            return False

        logger.info("Executor task start requested: execution_id=%s", execution_id)

        self._stop_token = StopToken()
        self._thread = QThread(self)
        self._worker = ExecutorWorker(
            execution_id=execution_id,
            runtime_context=runtime_context,
            stop_token=self._stop_token,
        )

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)

        self._worker.completed.connect(self.completed)
        self._worker.stopped.connect(self.stopped)
        self._worker.failed.connect(self.failed)
        self._worker.log.connect(self.log)
        self._worker.progress.connect(self.progress)

        self._worker.completed.connect(self._thread.quit)
        self._worker.stopped.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)

        self._worker.completed.connect(self._worker.deleteLater)
        self._worker.stopped.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)

        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_current_task)

        self._thread.start()
        return True

    def request_stop(self) -> bool:
        if self._stop_token is None:
            return False

        logger.info("Executor stop requested")
        self._stop_token.request_stop()
        return True

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _clear_current_task(self) -> None:
        self._thread = None
        self._worker = None
        self._stop_token = None
