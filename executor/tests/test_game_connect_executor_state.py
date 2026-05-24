"""P2-04/P2-05 执行器运行状态机测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from PySide6.QtWidgets import QMessageBox

from nzfz_executor.core.executor.options import ExecutorLaunchOptions
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import (
    ConnectedWindow,
    HealthCheckResult,
    HealthStatus,
    WindowInfo,
    WindowRect,
)
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

        self.start_calls: list[
            tuple[int, ExecutorRuntimeContext | None, ExecutorLaunchOptions | None]
        ] = []
        self.stop_calls = 0
        self._running = False
        self.next_start_result = True

    def start(
        self,
        execution_id: int,
        runtime_context: ExecutorRuntimeContext | None,
        launch_options: ExecutorLaunchOptions | None = None,
        repo_root=None,
    ) -> bool:
        self.start_calls.append((execution_id, runtime_context, launch_options))
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


def _set_real_input_mode(tab: GameConnectTab) -> None:
    tab._action_dry_run = False
    tab._action_dry_run_checkbox.setChecked(False)


def _auto_confirm_real_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )


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

    def test_connected_not_ready_becomes_ready_when_dry_run(
        self,
        tab: GameConnectTab,
    ) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._start_executor_button.isEnabled() is True
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_READY_BACKGROUND,
        )

    def test_connected_not_ready_stays_not_ready_when_real_click(
        self,
        tab: GameConnectTab,
    ) -> None:
        _set_real_input_mode(tab)
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._start_executor_button.isEnabled() is True
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_READY,
        )

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

    def test_start_from_not_ready_when_dry_run(self, tab: GameConnectTab) -> None:
        connected = _fake_connected()
        tab._window_manager.get_connected_context.return_value = connected
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        runner = tab._executor_task_runner
        assert isinstance(runner, FakeExecutorTaskRunner)

        tab._on_start_executor_clicked()
        assert tab._executor_state == ExecutorRunState.RUNNING
        assert len(runner.start_calls) == 1

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


class TestRuntimeContextInjection:
    def test_start_creates_runtime_context(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()

        assert len(runner.start_calls) == 1
        runtime_context = runner.start_calls[0][1]
        launch_options = runner.start_calls[0][2]
        assert launch_options is not None
        assert launch_options.script_path
        assert isinstance(runtime_context, ExecutorRuntimeContext)

    def test_runtime_context_contains_components(self, tab: GameConnectTab) -> None:
        from nzfz_executor.core.actions.backends import DryRunMouseBackend
        from nzfz_executor.core.actions.mouse_controller import MouseController
        from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
        from nzfz_executor.core.vision.template_matcher import TemplateMatcherRecognizer

        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()

        runtime_context = runner.start_calls[0][1]
        launch_options = runner.start_calls[0][2]
        assert launch_options is not None
        assert launch_options.script_path
        assert runtime_context is not None
        assert runtime_context.screenshot_manager is tab._screenshot_manager
        assert isinstance(runtime_context.recognizer, TemplateMatcherRecognizer)
        assert isinstance(runtime_context.coordinate_mapper, CoordinateMapper)
        assert isinstance(runtime_context.mouse_controller, MouseController)
        assert isinstance(
            runtime_context.mouse_controller._backend,
            DryRunMouseBackend,
        )
        from nzfz_executor.core.actions.backends.dry_run_keyboard_backend import (
            DryRunKeyboardBackend,
        )
        from nzfz_executor.core.actions.keyboard_controller import KeyboardController

        assert isinstance(runtime_context.keyboard_controller, KeyboardController)
        assert isinstance(
            runtime_context.keyboard_controller._backend,
            DryRunKeyboardBackend,
        )


class TestActionDryRunUi:
    def test_dry_run_checkbox_default_checked(self, tab: GameConnectTab) -> None:
        assert tab._action_dry_run_checkbox.isChecked() is True
        assert tab._action_dry_run is True

    def test_cancel_real_input_confirmation_does_not_start(
        self,
        tab: GameConnectTab,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_real_input_mode(tab)
        monkeypatch.setattr(
            "nzfz_executor.ui.tabs.game_connect.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Cancel,
        )
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()

        assert len(runner.start_calls) == 0
        assert tab._executor_state == ExecutorRunState.READY

    def test_real_input_launch_uses_send_input_backends(
        self,
        tab: GameConnectTab,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from nzfz_executor.core.actions.backends.send_input_backend import (
            SendInputMouseBackend,
        )
        from nzfz_executor.core.actions.backends.send_input_keyboard_backend import (
            SendInputKeyboardBackend,
        )

        _set_real_input_mode(tab)
        _auto_confirm_real_input(monkeypatch)
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()

        runtime_context = runner.start_calls[0][1]
        assert runtime_context is not None
        assert isinstance(runtime_context.mouse_controller._backend, SendInputMouseBackend)
        assert isinstance(
            runtime_context.keyboard_controller._backend,
            SendInputKeyboardBackend,
        )


class TestConnectionStateEffects:
    def test_running_connection_degraded_to_failed_when_real_click(
        self,
        tab: GameConnectTab,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_real_input_mode(tab)
        _auto_confirm_real_input(monkeypatch)
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.FAILED
        assert "连接状态异常" in tab._executor_status_label.text()
        assert runner.stop_calls == 1

    def test_running_connection_not_ready_continues_when_dry_run(
        self,
        tab: GameConnectTab,
    ) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.RUNNING
        assert runner.stop_calls == 0

    def test_start_with_activate_when_real_click_and_not_ready(
        self,
        tab: GameConnectTab,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_real_input_mode(tab)
        _auto_confirm_real_input(monkeypatch)
        connected = _fake_connected()
        tab._window_manager.get_connected_context.return_value = connected
        tab._window_manager.activate_connected_window.return_value = (True, "")
        tab._window_manager.check_health.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="窗口连接正常",
            window=connected,
            is_foreground=True,
        )
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        tab._set_executor_state(ExecutorRunState.READY)

        runner = tab._executor_task_runner
        assert isinstance(runner, FakeExecutorTaskRunner)
        tab._on_start_executor_clicked()

        tab._window_manager.activate_connected_window.assert_called_once()
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY
        assert tab._executor_state == ExecutorRunState.RUNNING
        assert len(runner.start_calls) == 1

    def test_start_activate_failed_when_real_click(
        self,
        tab: GameConnectTab,
    ) -> None:
        _set_real_input_mode(tab)
        connected = _fake_connected()
        tab._window_manager.get_connected_context.return_value = connected
        tab._window_manager.activate_connected_window.return_value = (False, "激活失败")
        tab._window_manager.check_health.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="窗口连接正常，但当前不在前台",
            window=connected,
            is_foreground=False,
        )
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)

        tab._on_start_executor_clicked()

        assert tab._executor_state == ExecutorRunState.READY
        assert tab._executor_status_label.text() == get_feedback_text(
            FeedbackCode.EXECUTOR_ACTIVATE_FAILED,
        )

    def test_running_connection_degraded_to_failed(self, tab: GameConnectTab) -> None:
        runner = _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._set_connection_state(ConnectionUiState.CONNECTED_UNHEALTHY)
        assert tab._executor_state == ExecutorRunState.FAILED
        assert "连接状态异常" in tab._executor_status_label.text()
        assert runner.stop_calls == 1

    def test_stopping_keeps_stopping_on_connection_change(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._set_executor_state(ExecutorRunState.STOPPING)
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._executor_state == ExecutorRunState.STOPPING
