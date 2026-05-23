"""P2-04/P2-05 执行器运行状态机测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.models import ConnectedWindow, WindowInfo, WindowRect
from nzfz_executor.ui.feedback import FeedbackCode, get_feedback_text
from nzfz_executor.ui.states import ExecutorRunState
from nzfz_executor.ui.tabs.game_connect import ConnectionUiState, GameConnectTab, SearchUiState


class FakeTaskRunner:
    """最小 TaskRunner 替身，避免后台线程。"""

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

    def start_search(self, request_id: int, keyword: str) -> None:
        self.search_calls.append((request_id, keyword))

    def start_connect(self, request_id: int, window_info: WindowInfo, options) -> None:
        pass

    def start_health_check(self, request_id: int) -> None:
        pass


class FakeScreenshotTaskRunner:
    def __init__(self, screenshot_manager, parent=None) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Emitter(QObject):
            capture_finished = Signal(int, object)
            capture_failed = Signal(int, str)

        self._emitter = _Emitter(parent)
        self.capture_finished = self._emitter.capture_finished
        self.capture_failed = self._emitter.capture_failed


class FakeExecutorTaskRunner:
    """可控 ExecutorTaskRunner 替身。"""

    def __init__(self, parent=None) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Emitter(QObject):
            completed = Signal(int)
            stopped = Signal(int)
            failed = Signal(int, str)
            log = Signal(int, str)
            progress = Signal(int, int, str)
            start_rejected = Signal(int, str)

        self._emitter = _Emitter(parent)
        self.completed = self._emitter.completed
        self.stopped = self._emitter.stopped
        self.failed = self._emitter.failed
        self.log = self._emitter.log
        self.progress = self._emitter.progress
        self.start_rejected = self._emitter.start_rejected

        self.start_calls: list[tuple[int, ConnectedWindow | None]] = []
        self.stop_calls = 0
        self._running = False
        self.next_start_result = True

    def start(self, execution_id: int, context: ConnectedWindow | None) -> bool:
        self.start_calls.append((execution_id, context))
        if not self.next_start_result:
            self.start_rejected.emit(execution_id, "当前已有任务正在运行")
            return False
        self._running = True
        return True

    def request_stop(self) -> bool:
        if not self._running:
            return False
        self.stop_calls += 1
        return True

    def is_running(self) -> bool:
        return self._running

    def emit_stopped(self, execution_id: int) -> None:
        self._running = False
        self.stopped.emit(execution_id)

    def emit_completed(self, execution_id: int) -> None:
        self._running = False
        self.completed.emit(execution_id)

    def emit_failed(self, execution_id: int, message: str) -> None:
        self._running = False
        self.failed.emit(execution_id, message)


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
    fake_executor_holder: dict[str, FakeExecutorTaskRunner] = {}
    mock_manager = MagicMock()
    mock_manager.is_connected.return_value = False
    mock_manager.get_connected_context.return_value = None

    def _window_factory(window_manager, parent=None):
        runner = FakeTaskRunner(window_manager, parent)
        fake_runner_holder["runner"] = runner
        return runner

    def _screenshot_factory(screenshot_manager, parent=None):
        return FakeScreenshotTaskRunner(screenshot_manager, parent)

    def _executor_factory(parent=None):
        runner = FakeExecutorTaskRunner(parent)
        fake_executor_holder["runner"] = runner
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
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.ExecutorTaskRunner",
        _executor_factory,
    )
    widget = GameConnectTab()
    widget._window_manager = mock_manager
    widget._task_runner = fake_runner_holder["runner"]
    widget._executor_task_runner = fake_executor_holder["runner"]
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


def _select_row(tab: GameConnectTab, row: int = 0) -> None:
    tab._result_table.selectRow(row)


def _prepare_ready_tab(tab: GameConnectTab) -> FakeExecutorTaskRunner:
    connected = _fake_connected()
    tab._window_manager.get_connected_context.return_value = connected
    tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
    runner = tab._executor_task_runner
    assert isinstance(runner, FakeExecutorTaskRunner)
    return runner


class TestExecutorInitialState:
    def test_initial_not_ready(self, tab: GameConnectTab) -> None:
        assert tab._executor_state == ExecutorRunState.NOT_READY
        assert tab._start_executor_button.isEnabled() is False
        assert tab._stop_executor_button.isEnabled() is False
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_NOT_READY,
        )


class TestExecutorReadyState:
    def test_connected_ready_becomes_ready(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._start_executor_button.isEnabled() is True

    def test_connected_not_ready_stays_not_ready(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.NOT_READY

    def test_disconnected_not_ready(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_connection_state(ConnectionUiState.DISCONNECTED)
        assert tab._executor_state == ExecutorRunState.NOT_READY


class TestStartStopFlow:
    def test_start_from_ready_enters_running(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        assert tab._executor_state == ExecutorRunState.RUNNING
        assert len(runner.start_calls) == 1
        assert tab._start_executor_button.isEnabled() is False
        assert tab._stop_executor_button.isEnabled() is True

    def test_start_blocked_when_not_ready(self, tab: GameConnectTab) -> None:
        tab._on_start_executor_clicked()
        assert tab._executor_state == ExecutorRunState.NOT_READY
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_START_BLOCKED,
        )

    def test_stop_from_running_returns_ready_when_connected(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None

        tab._on_stop_executor_clicked()
        assert tab._executor_state == ExecutorRunState.STOPPING
        assert runner.stop_calls == 1

        runner.emit_stopped(execution_id)
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._stop_executor_button.isEnabled() is False

    def test_stop_no_effect_when_not_running(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_stop_executor_clicked()
        assert tab._executor_state == ExecutorRunState.READY

    def test_stopping_disables_stop_button(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._set_executor_state(ExecutorRunState.STOPPING)
        assert tab._stop_executor_button.isEnabled() is False


class TestAsyncExecutionResults:
    def test_completed_returns_ready(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None

        runner.emit_completed(execution_id)
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._active_execution_id is None

    def test_failed_clears_active_execution(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None

        runner.emit_failed(execution_id, "任务执行失败")
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._active_execution_id is None

    def test_start_rejected_clears_active_execution(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        runner.next_start_result = False
        tab._on_start_executor_clicked()
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._active_execution_id is None

    def test_stop_timeout_clears_active_execution(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        assert tab._active_execution_id is not None

        tab._on_stop_executor_clicked()
        tab._on_executor_stop_timeout()
        assert tab._active_execution_id is None
        assert tab._executor_state == ExecutorRunState.READY

    def test_stale_completed_is_discarded(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None

        tab._active_execution_id = None
        runner.emit_completed(execution_id)
        assert tab._executor_state == ExecutorRunState.RUNNING

    def test_generation_mismatch_discards_completed(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None

        tab._connection_generation += 1
        runner.emit_completed(execution_id)
        assert tab._executor_state == ExecutorRunState.RUNNING


class TestConnectionRestrictions:
    def test_running_disables_search_connect_disconnect(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        _select_row(tab)
        tab._set_executor_state(ExecutorRunState.RUNNING)

        assert tab._search_btn.isEnabled() is False
        assert tab._connect_btn.isEnabled() is False
        assert tab._disconnect_btn.isEnabled() is False

    def test_running_blocks_connect_entry(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        _select_row(tab)
        tab._set_executor_state(ExecutorRunState.RUNNING)

        tab._on_connect()
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_STOP_REQUIRED,
        )

    def test_running_blocks_disconnect_entry(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.RUNNING)

        tab._on_disconnect()
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY

    def test_running_blocks_search_entry(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.RUNNING)

        tab._search_input.setText("game")
        tab._trigger_immediate_search()
        assert tab._task_runner.search_calls == []

    def test_stopping_disables_connection_controls(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.STOPPING)
        assert tab._connect_btn.isEnabled() is False
        assert tab._disconnect_btn.isEnabled() is False


class TestScreenshotRestrictions:
    def test_running_disables_screenshot_refresh(self, tab: GameConnectTab) -> None:
        tab._window_manager.get_connected_context.return_value = _fake_connected()
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.RUNNING)
        assert tab._refresh_screenshot_button.isEnabled() is False

    def test_capturing_disables_start_executor(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._is_capturing = True
        tab._refresh_executor_ready_state()
        assert tab._executor_state == ExecutorRunState.NOT_READY
        assert tab._start_executor_button.isEnabled() is False

    def test_capture_end_restores_ready(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._is_capturing = True
        tab._refresh_executor_ready_state()
        tab._is_capturing = False
        tab._refresh_executor_ready_state()
        assert tab._executor_state == ExecutorRunState.READY


class TestConnectionStateEffects:
    def test_running_connection_degraded_to_failed(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.FAILED
        assert "连接状态异常" in tab._executor_status_label.text()
        assert runner.stop_calls == 1

    def test_stopping_keeps_stopping_on_connection_change(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.STOPPING)
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.STOPPING
