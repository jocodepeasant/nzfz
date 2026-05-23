"""P2-02 游戏连接页截图预览与手动刷新测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from PIL import Image

from nzfz_executor.core.models import (
    CaptureBackendType,
    CaptureRegion,
    ConnectedWindow,
    ScreenshotResult,
    WindowRect,
)
from nzfz_executor.ui.feedback import FeedbackCode, get_feedback_text
from nzfz_executor.ui.tabs.game_connect import ConnectionUiState, GameConnectTab


class FakeTaskRunner:
    def __init__(self, window_manager, parent=None) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Emitter(QObject):
            search_finished = Signal(int, list)
            search_failed = Signal(int, str)
            connect_finished = Signal(int, object)
            connect_failed = Signal(int, str)
            health_finished = Signal(int, object)
            health_failed = Signal(int, str)

        self._emitter = _Emitter(parent)
        self.search_finished = self._emitter.search_finished
        self.search_failed = self._emitter.search_failed
        self.connect_finished = self._emitter.connect_finished
        self.connect_failed = self._emitter.connect_failed
        self.health_finished = self._emitter.health_finished
        self.health_failed = self._emitter.health_failed
        self.window_manager = window_manager
        self.search_calls: list[tuple[int, str]] = []
        self.connect_calls: list = []
        self.health_calls: list[int] = []

    def start_search(self, request_id: int, keyword: str) -> None:
        self.search_calls.append((request_id, keyword))

    def start_connect(self, request_id: int, window_info, options) -> None:
        self.connect_calls.append((request_id, window_info))

    def start_health_check(self, request_id: int) -> None:
        self.health_calls.append(request_id)


class FakeScreenshotTaskRunner:
    def __init__(self, screenshot_manager, parent=None) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Emitter(QObject):
            capture_finished = Signal(int, object)
            capture_failed = Signal(int, str)

        self._emitter = _Emitter(parent)
        self.capture_finished = self._emitter.capture_finished
        self.capture_failed = self._emitter.capture_failed
        self.screenshot_manager = screenshot_manager
        self.capture_calls: list = []

    def start_capture(self, request_id: int, context, options) -> None:
        self.capture_calls.append((request_id, context, options))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _connected_window(**kwargs) -> ConnectedWindow:
    defaults = dict(
        hwnd=100,
        title="Game",
        process_name="game.exe",
        pid=200,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 560),
    )
    defaults.update(kwargs)
    return ConnectedWindow(**defaults)


def _success_result(**kwargs) -> ScreenshotResult:
    image = Image.new("RGB", (128, 72), color=(10, 20, 30))
    defaults = dict(
        success=True,
        image=image,
        width=128,
        height=72,
        captured_at=datetime(2026, 5, 23, 23, 15, 12),
        hwnd=100,
        window_title="Game",
        region=CaptureRegion.CLIENT,
        backend=CaptureBackendType.SCREEN,
        supports_occluded=False,
        message="",
    )
    defaults.update(kwargs)
    return ScreenshotResult(**defaults)


@pytest.fixture
def tab(qapp, monkeypatch):
    fake_window_runner_holder: dict[str, FakeTaskRunner] = {}
    fake_screenshot_runner_holder: dict[str, FakeScreenshotTaskRunner] = {}

    mock_manager = MagicMock()
    mock_manager.is_connected.return_value = False
    mock_manager.get_connected_context.return_value = None

    def _window_factory(window_manager, parent=None):
        runner = FakeTaskRunner(window_manager, parent)
        fake_window_runner_holder["runner"] = runner
        return runner

    def _screenshot_factory(screenshot_manager, parent=None):
        runner = FakeScreenshotTaskRunner(screenshot_manager, parent)
        fake_screenshot_runner_holder["runner"] = runner
        return runner

    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.WindowManager",
        lambda: mock_manager,
    )
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.WindowTaskRunner",
        _window_factory,
    )
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.ScreenshotTaskRunner",
        _screenshot_factory,
    )

    widget = GameConnectTab()
    widget._window_manager = mock_manager
    widget._task_runner = fake_window_runner_holder["runner"]
    widget._screenshot_task_runner = fake_screenshot_runner_holder["runner"]
    return widget


def _connect_tab(tab: GameConnectTab) -> None:
    context = _connected_window()
    tab._window_manager.get_connected_context.return_value = context
    tab._window_manager.is_connected.return_value = True
    tab._connection_state = ConnectionUiState.CONNECTED_READY
    tab._apply_ui_state()


class TestScreenshotUiInit:
    def test_preview_area_exists(self, tab: GameConnectTab) -> None:
        assert tab._screenshot_preview_label is not None
        assert tab._refresh_screenshot_button is not None
        assert tab._screenshot_status_label is not None
        assert tab._screenshot_meta_label is not None

    def test_initial_preview_text(self, tab: GameConnectTab) -> None:
        assert tab._screenshot_preview_label.text() == "暂无截图"

    def test_refresh_button_disabled_when_disconnected(self, tab: GameConnectTab) -> None:
        assert not tab._refresh_screenshot_button.isEnabled()


class TestScreenshotButtonState:
    def test_enabled_when_connected(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        assert tab._refresh_screenshot_button.isEnabled()

    def test_disabled_when_connecting(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._connecting = True
        tab._update_screenshot_button_state()
        assert not tab._refresh_screenshot_button.isEnabled()

    def test_disabled_while_capturing(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._is_capturing = True
        tab._update_screenshot_button_state()
        assert not tab._refresh_screenshot_button.isEnabled()


class TestScreenshotCaptureFlow:
    def test_click_starts_async_capture(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()

        assert len(tab._screenshot_task_runner.capture_calls) == 1
        request_id, context, options = tab._screenshot_task_runner.capture_calls[0]
        assert request_id == 1
        assert context is not None
        assert options.region == CaptureRegion.CLIENT
        assert tab._is_capturing
        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_CAPTURING,
        )

    def test_unavailable_when_not_connected(self, tab: GameConnectTab) -> None:
        tab._on_refresh_screenshot_clicked()
        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_UNAVAILABLE,
        )
        assert len(tab._screenshot_task_runner.capture_calls) == 0

    def test_no_stacking_while_capturing(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._is_capturing = True
        tab._on_refresh_screenshot_clicked()
        assert len(tab._screenshot_task_runner.capture_calls) == 0

    def test_success_shows_preview_and_meta(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        result = _success_result()
        tab._screenshot_task_runner.capture_finished.emit(1, result)

        assert tab._last_screenshot_pixmap is not None
        assert tab._screenshot_preview_label.pixmap() is not None
        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_SUCCESS,
        )
        assert "128 x 72" in tab._screenshot_meta_label.text()
        assert "screen" in tab._screenshot_meta_label.text()
        assert not tab._is_capturing
        assert tab._refresh_screenshot_button.isEnabled()

    def test_failure_keeps_previous_preview(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        previous = tab._last_screenshot_pixmap
        tab._on_refresh_screenshot_clicked()
        tab._screenshot_task_runner.capture_finished.emit(
            2,
            ScreenshotResult(success=False, message="窗口已最小化，无法截图"),
        )

        assert tab._last_screenshot_pixmap is previous
        assert tab._screenshot_status_label.text() == "窗口已最小化，无法截图"

    def test_worker_failure_shows_standard_message(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._screenshot_task_runner.capture_failed.emit(1, "boom")

        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_FAILED,
        )
        assert not tab._is_capturing


class TestScreenshotTimeout:
    def test_timeout_restores_button(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._on_capture_timeout()

        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_TIMEOUT,
        )
        assert not tab._is_capturing
        assert tab._refresh_screenshot_button.isEnabled()

    def test_late_result_discarded_after_timeout(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._on_capture_timeout()
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        assert tab._last_screenshot_pixmap is None
        assert tab._screenshot_preview_label.text() == "暂无截图"


class TestScreenshotRequestGuards:
    def test_old_request_discarded(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._active_capture_request_id = 99
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        assert tab._last_screenshot_pixmap is None

    def test_generation_mismatch_discarded(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._connection_generation += 1
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        assert tab._last_screenshot_pixmap is None


class TestScreenshotDisconnect:
    def test_disconnect_clears_preview(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        tab._do_disconnect()

        assert tab._last_screenshot_pixmap is None
        assert tab._screenshot_preview_label.text() == "暂无截图"
        assert tab._screenshot_meta_label.text() == ""
        assert not tab._refresh_screenshot_button.isEnabled()
        assert tab._screenshot_status_label.text() == get_feedback_text(
            FeedbackCode.SCREENSHOT_UNAVAILABLE,
        )

    def test_switch_clears_preview(self, tab: GameConnectTab) -> None:
        _connect_tab(tab)
        tab._on_refresh_screenshot_clicked()
        tab._screenshot_task_runner.capture_finished.emit(1, _success_result())

        tab._disconnect_for_switch()

        assert tab._last_screenshot_pixmap is None
        assert tab._screenshot_preview_label.text() == "暂无截图"


class TestPilToPixmap:
    def test_pil_image_to_pixmap(self, tab: GameConnectTab) -> None:
        image = Image.new("RGB", (64, 48), color=(255, 0, 0))
        pixmap = tab._pil_image_to_pixmap(image)
        assert not pixmap.isNull()
        assert pixmap.width() == 64
        assert pixmap.height() == 48

    def test_set_screenshot_pixmap_scales(self, tab: GameConnectTab) -> None:
        image = Image.new("RGB", (200, 100), color=(0, 255, 0))
        pixmap = tab._pil_image_to_pixmap(image)
        tab._set_screenshot_pixmap(pixmap)

        displayed = tab._screenshot_preview_label.pixmap()
        assert displayed is not None
        assert displayed.width() <= tab._screenshot_preview_label.width()
        assert displayed.height() <= tab._screenshot_preview_label.height()


class TestScreenshotCaptureWorker:
    def test_worker_emits_finished(self, qapp) -> None:
        from nzfz_executor.ui.workers.screenshot_workers import ScreenshotCaptureWorker

        manager = MagicMock()
        result = _success_result()
        manager.capture.return_value = result
        context = _connected_window()
        options = MagicMock()

        worker = ScreenshotCaptureWorker(7, manager, context, options)
        received: list = []

        worker.finished.connect(lambda rid, res: received.append((rid, res)))
        worker.run()

        assert received == [(7, result)]
        manager.capture.assert_called_once_with(context, options)

    def test_worker_emits_failed_on_exception(self, qapp) -> None:
        from nzfz_executor.ui.workers.screenshot_workers import ScreenshotCaptureWorker

        manager = MagicMock()
        manager.capture.side_effect = RuntimeError("capture boom")

        worker = ScreenshotCaptureWorker(3, manager, None, MagicMock())
        errors: list = []
        worker.failed.connect(lambda rid, msg: errors.append((rid, msg)))
        worker.run()

        assert errors[0][0] == 3
        assert "capture boom" in errors[0][1]
