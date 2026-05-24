"""窗口任务运行器：统一管理 Worker 与 QThread 生命周期。"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from nzfz_executor.core.models import ConnectOptions, WindowInfo
from nzfz_executor.core.window_manager import WindowManager

from nzfz_executor.ui.workers.window_workers import (
    WindowConnectWorker,
    WindowHealthCheckWorker,
    WindowSearchWorker,
)


class WindowTaskRunner(QObject):
    """将 WindowManager 同步调用包装为后台线程任务。"""

    search_finished = Signal(int, list)
    search_failed = Signal(int, str)

    connect_finished = Signal(int, object)
    connect_failed = Signal(int, str)

    health_finished = Signal(int, object)
    health_failed = Signal(int, str)

    def __init__(
        self,
        window_manager: WindowManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._window_manager = window_manager
        self._tasks: dict[str, tuple[QThread, QObject]] = {}

    def start_search(self, request_id: int, keyword: str) -> None:
        worker = WindowSearchWorker(
            request_id=request_id,
            window_manager=self._window_manager,
            keyword=keyword,
        )
        self._start_task(
            task_key=f"search:{request_id}",
            worker=worker,
            finished_signal=worker.finished,
            failed_signal=worker.failed,
            outward_finished_signal=self.search_finished,
            outward_failed_signal=self.search_failed,
        )

    def start_connect(
        self,
        request_id: int,
        window_info: WindowInfo,
        options: ConnectOptions,
    ) -> None:
        worker = WindowConnectWorker(
            request_id=request_id,
            window_manager=self._window_manager,
            window_info=window_info,
            options=options,
        )
        self._start_task(
            task_key=f"connect:{request_id}",
            worker=worker,
            finished_signal=worker.finished,
            failed_signal=worker.failed,
            outward_finished_signal=self.connect_finished,
            outward_failed_signal=self.connect_failed,
        )

    def start_health_check(self, request_id: int) -> None:
        worker = WindowHealthCheckWorker(
            request_id=request_id,
            window_manager=self._window_manager,
        )
        self._start_task(
            task_key=f"health:{request_id}",
            worker=worker,
            finished_signal=worker.finished,
            failed_signal=worker.failed,
            outward_finished_signal=self.health_finished,
            outward_failed_signal=self.health_failed,
        )

    def _start_task(
        self,
        task_key: str,
        worker: QObject,
        finished_signal,
        failed_signal,
        outward_finished_signal,
        outward_failed_signal,
    ) -> None:
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        finished_signal.connect(outward_finished_signal)
        failed_signal.connect(outward_failed_signal)

        finished_signal.connect(thread.quit)
        failed_signal.connect(thread.quit)

        finished_signal.connect(worker.deleteLater)
        failed_signal.connect(worker.deleteLater)

        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda key=task_key: self._cleanup_task(key))

        self._tasks[task_key] = (thread, worker)
        thread.start()

    def _cleanup_task(self, task_key: str) -> None:
        self._tasks.pop(task_key, None)
