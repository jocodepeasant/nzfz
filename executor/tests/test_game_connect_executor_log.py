"""P2-06 执行器日志与结果反馈 UI 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QPlainTextEdit

from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, WindowInfo, WindowRect
from nzfz_executor.ui.config.defaults import DEFAULT_MAX_EXECUTOR_LOG_LINES
from nzfz_executor.ui.models.executor_log import ExecutorLogLevel
from nzfz_executor.ui.states import ExecutorRunState
from nzfz_executor.ui.tabs.game_connect import ConnectionUiState, GameConnectTab


class FakeExecutorTaskRunner:
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
        self.next_start_result = True

    def start(
        self,
        execution_id: int,
        runtime_context: ExecutorRuntimeContext | None,
    ) -> bool:
        if not self.next_start_result:
            self.start_rejected.emit(execution_id, "当前已有任务正在运行")
            return False
        return True

    def request_stop(self) -> bool:
        return True

    def is_running(self) -> bool:
        return False

    def emit_completed(self, execution_id: int) -> None:
        self.completed.emit(execution_id)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tab(qapp, monkeypatch):
    fake_executor_holder: dict[str, FakeExecutorTaskRunner] = {}
    mock_manager = MagicMock()
    mock_manager.get_connected_context.return_value = None

    def _executor_factory(parent=None):
        runner = FakeExecutorTaskRunner(parent)
        fake_executor_holder["runner"] = runner
        return runner

    monkeypatch.setattr("nzfz_executor.ui.tabs.game_connect.WindowManager", lambda: mock_manager)
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.WindowTaskRunner",
        lambda wm, parent=None: MagicMock(),
    )
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.ScreenshotTaskRunner",
        lambda sm, parent=None: MagicMock(),
    )
    monkeypatch.setattr(
        "nzfz_executor.ui.tabs.game_connect.ExecutorTaskRunner",
        _executor_factory,
    )
    widget = GameConnectTab()
    widget._window_manager = mock_manager
    widget._executor_task_runner = fake_executor_holder["runner"]
    return widget


def _fake_connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


def _prepare_ready_tab(tab: GameConnectTab) -> None:
    tab._window_manager.get_connected_context.return_value = _fake_connected()
    tab._set_connection_state(ConnectionUiState.CONNECTED_READY)


class TestExecutorLogUiInit:
    def test_log_area_readonly(self, tab: GameConnectTab) -> None:
        assert tab._executor_log_text_edit.isReadOnly() is True
        assert (
            tab._executor_log_text_edit.lineWrapMode()
            == QPlainTextEdit.LineWrapMode.NoWrap
        )

    def test_initial_progress_and_step(self, tab: GameConnectTab) -> None:
        assert tab._executor_progress_bar.value() == 0
        assert tab._executor_step_label.text() == "当前步骤：-"

    def test_max_log_lines_default(self, tab: GameConnectTab) -> None:
        assert tab._max_executor_log_lines == DEFAULT_MAX_EXECUTOR_LOG_LINES


class TestExecutorLogAppend:
    def test_append_info_log(self, tab: GameConnectTab) -> None:
        tab._append_executor_log(ExecutorLogLevel.INFO, "测试日志")
        assert len(tab._executor_log_entries) == 1
        assert "[INFO] 测试日志" in tab._executor_log_text_edit.toPlainText()

    def test_log_limit_removes_oldest(self, tab: GameConnectTab) -> None:
        tab._max_executor_log_lines = 3
        for i in range(4):
            tab._append_executor_log(ExecutorLogLevel.INFO, f"line-{i}")
        assert len(tab._executor_log_entries) == 3
        assert tab._executor_log_entries[0].message == "line-1"
        assert "line-0" not in tab._executor_log_text_edit.toPlainText()

    def test_clear_logs(self, tab: GameConnectTab) -> None:
        tab._append_executor_log(ExecutorLogLevel.INFO, "待清空")
        tab._clear_executor_logs()
        assert tab._executor_log_entries == []
        assert tab._executor_log_text_edit.toPlainText() == ""


class TestExecutorProgress:
    def test_update_progress_clamps(self, tab: GameConnectTab) -> None:
        tab._update_executor_progress(-5, "low")
        assert tab._executor_progress_bar.value() == 0
        tab._update_executor_progress(150, "high")
        assert tab._executor_progress_bar.value() == 100
        assert tab._executor_step_label.text() == "当前步骤：high"

    def test_progress_signal_updates_ui(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None
        tab._on_executor_progress(execution_id, 50, "步骤 10/20")
        assert tab._executor_progress_bar.value() == 50
        assert "步骤 10/20" in tab._executor_step_label.text()


class TestExecutorEventLogs:
    def test_start_writes_prepare_and_started_logs(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        text = tab._executor_log_text_edit.toPlainText()
        assert "准备启动执行任务" in text
        assert "执行任务已启动" in text
        assert "[SUCCESS]" in text

    def test_completed_writes_success_log(self, tab: GameConnectTab) -> None:
        runner = tab._executor_task_runner
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        execution_id = tab._active_execution_id
        assert execution_id is not None
        runner.emit_completed(execution_id)
        assert "任务执行完成" in tab._executor_log_text_edit.toPlainText()
        assert tab._executor_progress_bar.value() == 100

    def test_stale_log_not_shown(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        tab._active_execution_id = None
        tab._on_executor_log(999, "过期日志")
        assert "过期日志" not in tab._executor_log_text_edit.toPlainText()

    def test_clear_allowed_while_running(self, tab: GameConnectTab) -> None:
        _prepare_ready_tab(tab)
        tab._on_start_executor_clicked()
        assert tab._executor_state == ExecutorRunState.RUNNING
        tab._clear_executor_logs()
        tab._append_executor_log(ExecutorLogLevel.INFO, "新日志")
        assert "新日志" in tab._executor_log_text_edit.toPlainText()
