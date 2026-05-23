"""P1-05 游戏连接页用户反馈测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from nzfz_executor.core.models import (
    ConnectResult,
    ConnectedWindow,
    HealthCheckResult,
    HealthStatus,
    WindowInfo,
    WindowRect,
)
from nzfz_executor.ui.feedback import FeedbackCode, get_feedback_text
from nzfz_executor.ui.tabs.game_connect import (
    ConnectionUiState,
    GameConnectTab,
    SearchUiState,
)


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
        self.connect_calls: list[tuple[int, WindowInfo]] = []
        self.health_calls: list[int] = []

    def start_search(self, request_id: int, keyword: str) -> None:
        self.search_calls.append((request_id, keyword))

    def start_connect(self, request_id: int, window_info: WindowInfo, options) -> None:
        self.connect_calls.append((request_id, window_info))

    def start_health_check(self, request_id: int) -> None:
        self.health_calls.append(request_id)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tab(qapp, monkeypatch):
    fake_runner_holder: dict[str, FakeTaskRunner] = {}
    mock_manager = MagicMock()
    mock_manager.is_connected.return_value = False

    def _factory(window_manager, parent=None):
        runner = FakeTaskRunner(window_manager, parent)
        fake_runner_holder["runner"] = runner
        return runner

    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.WindowManager",
        lambda: mock_manager,
    )
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.WindowTaskRunner",
        _factory,
    )
    widget = GameConnectTab()
    widget._window_manager = mock_manager
    widget._task_runner = fake_runner_holder["runner"]
    return widget


def _fake_window_info(**kwargs) -> WindowInfo:
    defaults = dict(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        width=800,
        height=600,
        match_score=1.0,
    )
    defaults.update(kwargs)
    return WindowInfo(**defaults)


def _fake_connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


class TestSearchFeedback:
    def test_empty_keyword_shows_input_required(self, tab: GameConnectTab) -> None:
        tab._handle_empty_keyword()
        assert tab._search_status_label.text() == get_feedback_text(
            FeedbackCode.SEARCH_INPUT_REQUIRED,
        )

    def test_search_failed_hides_worker_message(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._search_running = True
        tab._on_search_failed(1, "AttributeError: secret internal detail")
        assert "AttributeError" not in tab._search_status_label.text()
        assert tab._search_status_label.text() == get_feedback_text(
            FeedbackCode.SEARCH_FAILED,
        )

    def test_search_timeout_standard_text(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._on_search_timeout(1)
        assert tab._search_status_label.text() == get_feedback_text(
            FeedbackCode.SEARCH_TIMEOUT,
        )


class TestConnectFeedback:
    def test_connect_success_ready_text(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_finished(1, ConnectResult.ok(_fake_connected()))
        assert tab._status_text.text() == get_feedback_text(
            FeedbackCode.CONNECT_SUCCESS_READY,
        )

    def test_connect_failed_with_error_message(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        result = ConnectResult.fail("窗口已最小化，请恢复窗口后重试")
        tab._on_connect_finished(1, result)
        assert tab._status_text.text() == "窗口已最小化，请恢复窗口后重试"

    def test_connect_failed_without_error_message(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        result = ConnectResult.fail("")
        tab._on_connect_finished(1, result)
        assert tab._status_text.text() == get_feedback_text(FeedbackCode.CONNECT_FAILED)

    def test_connect_worker_exception_standard_text(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_failed(1, "RuntimeError: boom")
        assert "RuntimeError" not in tab._status_text.text()
        assert tab._status_text.text() == get_feedback_text(FeedbackCode.CONNECT_EXCEPTION)

    def test_disconnect_success_text(self, tab: GameConnectTab) -> None:
        tab._do_disconnect()
        assert tab._status_text.text() == get_feedback_text(
            FeedbackCode.DISCONNECT_SUCCESS,
        )


class TestHealthFeedback:
    def test_health_ready_execute_label(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        health = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="ok",
            window=_fake_connected(),
            is_foreground=True,
        )
        tab._on_health_finished(1, health)
        assert tab._execute_status_label.text() == get_feedback_text(
            FeedbackCode.HEALTH_READY,
        )

    def test_health_not_ready_execute_label(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        health = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="",
            window=_fake_connected(),
            is_foreground=False,
        )
        tab._on_health_finished(1, health)
        assert tab._execute_status_label.text() == get_feedback_text(
            FeedbackCode.HEALTH_NOT_READY_FOREGROUND,
        )

    def test_health_worker_exception_standard_text(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        tab._health_check_running = True
        tab._on_health_failed(1, "ValueError: internal")
        assert "ValueError" not in tab._execute_status_label.text()
        assert tab._execute_status_label.text() == get_feedback_text(
            FeedbackCode.HEALTH_EXCEPTION,
        )


class TestWindowHintFeedback:
    def test_minimized_selection_hint(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info(is_minimized=True)])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._result_table.selectRow(0)
        tab._on_selection_changed()
        assert tab._status_label.text() == get_feedback_text(FeedbackCode.WINDOW_MINIMIZED)


class TestConfirmDialog:
    def test_switch_connection_uses_standard_copy(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as mock_q:
            tab._confirm_switch_connection(_fake_window_info())
            title = mock_q.call_args[0][1]
            message = mock_q.call_args[0][2]
            assert title == get_feedback_text(FeedbackCode.CONFIRM_SWITCH_CONNECTION_TITLE)
            assert message == get_feedback_text(FeedbackCode.CONFIRM_SWITCH_CONNECTION_MESSAGE)

    def test_connect_failure_does_not_open_dialog(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        with patch.object(QMessageBox, "question") as mock_q:
            tab._on_connect_failed(1, "err")
            mock_q.assert_not_called()
