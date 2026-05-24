"""窗口相关 UI Worker：在后台线程执行 WindowManager 同步方法。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from nzfz_executor.core.models import ConnectOptions, WindowInfo
from nzfz_executor.core.window_manager import WindowManager


class WindowSearchWorker(QObject):
    """异步执行 WindowManager.search_windows。"""

    finished = Signal(int, list)
    failed = Signal(int, str)

    def __init__(
        self,
        request_id: int,
        window_manager: WindowManager,
        keyword: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request_id = request_id
        self._window_manager = window_manager
        self._keyword = keyword

    @Slot()
    def run(self) -> None:
        try:
            results = self._window_manager.search_windows(self._keyword)
            self.finished.emit(self._request_id, results)
        except Exception as error:
            self.failed.emit(
                self._request_id,
                f"任务执行异常：{error}",
            )


class WindowConnectWorker(QObject):
    """异步执行 WindowManager.connect_window。"""

    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(
        self,
        request_id: int,
        window_manager: WindowManager,
        window_info: WindowInfo,
        options: ConnectOptions,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request_id = request_id
        self._window_manager = window_manager
        self._window_info = window_info
        self._options = options

    @Slot()
    def run(self) -> None:
        try:
            result = self._window_manager.connect_window(
                self._window_info,
                self._options,
            )
            self.finished.emit(self._request_id, result)
        except Exception as error:
            self.failed.emit(
                self._request_id,
                f"任务执行异常：{error}",
            )


class WindowHealthCheckWorker(QObject):
    """异步执行 WindowManager.check_health。"""

    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(
        self,
        request_id: int,
        window_manager: WindowManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request_id = request_id
        self._window_manager = window_manager

    @Slot()
    def run(self) -> None:
        try:
            result = self._window_manager.check_health()
            self.finished.emit(self._request_id, result)
        except Exception as error:
            self.failed.emit(
                self._request_id,
                f"任务执行异常：{error}",
            )
