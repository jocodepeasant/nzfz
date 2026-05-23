"""截图相关 UI Worker：在后台线程执行 ScreenshotManager 同步方法。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from nzfz_executor.core.models import CaptureOptions, ConnectedWindow
from nzfz_executor.core.screenshot_manager import ScreenshotManager


class ScreenshotCaptureWorker(QObject):
    """异步执行 ScreenshotManager.capture。"""

    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(
        self,
        request_id: int,
        screenshot_manager: ScreenshotManager,
        context: ConnectedWindow | None,
        options: CaptureOptions,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request_id = request_id
        self._screenshot_manager = screenshot_manager
        self._context = context
        self._options = options

    @Slot()
    def run(self) -> None:
        try:
            result = self._screenshot_manager.capture(
                self._context,
                self._options,
            )
            self.finished.emit(self._request_id, result)
        except Exception as error:
            self.failed.emit(
                self._request_id,
                f"任务执行异常：{error}",
            )
