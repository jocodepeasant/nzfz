"""截图任务运行器：统一管理 ScreenshotCaptureWorker 与 QThread 生命周期。"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from nzfz_executor.core.models import CaptureOptions, ConnectedWindow
from nzfz_executor.core.screenshot_manager import ScreenshotManager

from nzfz_executor.ui.workers.screenshot_workers import ScreenshotCaptureWorker


class ScreenshotTaskRunner(QObject):
    """将 ScreenshotManager 同步调用包装为后台线程任务。"""

    capture_finished = Signal(int, object)
    capture_failed = Signal(int, str)

    def __init__(
        self,
        screenshot_manager: ScreenshotManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._screenshot_manager = screenshot_manager
        self._tasks: dict[str, tuple[QThread, QObject]] = {}

    def start_capture(
        self,
        request_id: int,
        context: ConnectedWindow | None,
        options: CaptureOptions,
    ) -> None:
        worker = ScreenshotCaptureWorker(
            request_id=request_id,
            screenshot_manager=self._screenshot_manager,
            context=context,
            options=options,
        )
        self._start_task(
            task_key=f"capture:{request_id}",
            worker=worker,
            finished_signal=worker.finished,
            failed_signal=worker.failed,
            outward_finished_signal=self.capture_finished,
            outward_failed_signal=self.capture_failed,
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
