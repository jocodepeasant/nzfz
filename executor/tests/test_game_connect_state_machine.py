"""P1-04 游戏连接页 UI 状态机测试。"""

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
from nzfz_executor.ui.states import ExecutorRunState
from nzfz_executor.ui.tabs.game_connect import (
    ConnectionUiState,
    GameConnectTab,
    SearchUiState,
)


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


def _select_row(tab: GameConnectTab, row: int = 0) -> None:
    tab._result_table.selectRow(row)


class TestSearchUiState:
    def test_initial_state_idle(self, tab: GameConnectTab) -> None:
        assert tab._search_state == SearchUiState.IDLE

    def test_start_search_enters_searching(self, tab: GameConnectTab) -> None:
        tab._search_input.setText("game")
        tab._trigger_immediate_search()
        assert tab._search_state == SearchUiState.SEARCHING
        assert tab._connect_btn.isEnabled() is False

    def test_search_success_with_results(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._search_running = True
        tab._on_search_finished(1, [_fake_window_info()])
        assert tab._search_state == SearchUiState.HAS_RESULT
        assert len(tab._search_results) == 1

    def test_search_success_empty(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._search_running = True
        tab._on_search_finished(1, [])
        assert tab._search_state == SearchUiState.EMPTY
        assert tab._search_results == []
        assert tab._result_table.rowCount() == 0

    def test_search_failed_clears_results(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._search_running = True
        tab._fill_search_results([_fake_window_info()])
        tab._on_search_failed(1, "boom")
        assert tab._search_state == SearchUiState.ERROR
        assert tab._search_results == []

    def test_search_timeout_clears_results(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 1
        tab._fill_search_results([_fake_window_info()])
        tab._on_search_timeout(1)
        assert tab._search_state == SearchUiState.ERROR
        assert tab._search_results == []

    def test_empty_keyword_idle(self, tab: GameConnectTab) -> None:
        tab._search_results = [_fake_window_info()]
        tab._handle_empty_keyword()
        assert tab._search_state == SearchUiState.IDLE
        assert tab._search_results == []


class TestConnectionUiState:
    def test_initial_disconnected(self, tab: GameConnectTab) -> None:
        assert tab._connection_state == ConnectionUiState.DISCONNECTED

    def test_start_connect(self, tab: GameConnectTab) -> None:
        tab._start_connect(_fake_window_info())
        assert tab._connection_state == ConnectionUiState.CONNECTING

    def test_connect_success_ready(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_finished(1, ConnectResult.ok(_fake_connected()))
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY

    def test_connect_failure_disconnected(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_failed(1, "err")
        assert tab._connection_state == ConnectionUiState.DISCONNECTED

    def test_connect_timeout_disconnected(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_timeout(1)
        assert tab._connection_state == ConnectionUiState.DISCONNECTED

    def test_disconnect(self, tab: GameConnectTab) -> None:
        tab._connection_state = ConnectionUiState.CONNECTED_READY
        tab._do_disconnect()
        assert tab._connection_state == ConnectionUiState.DISCONNECTED

    def test_health_ready(self, tab: GameConnectTab) -> None:
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
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY

    def test_health_not_ready(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        health = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="窗口未在前台",
            window=_fake_connected(),
            is_foreground=False,
        )
        tab._on_health_finished(1, health)
        assert tab._connection_state == ConnectionUiState.CONNECTED_NOT_READY

    def test_health_unhealthy(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        health = HealthCheckResult(
            status=HealthStatus.HANDLE_INVALID,
            message="bad",
            window=_fake_connected(),
        )
        tab._on_health_finished(1, health)
        assert tab._connection_state == ConnectionUiState.CONNECTED_UNHEALTHY


class TestButtonStates:
    def test_initial_buttons_disabled(self, tab: GameConnectTab) -> None:
        assert tab._connect_btn.isEnabled() is False
        assert tab._disconnect_btn.isEnabled() is False
        assert tab._start_executor_button.isEnabled() is False
        assert tab._stop_executor_button.isEnabled() is False

    def test_searching_disables_search_and_connect(self, tab: GameConnectTab) -> None:
        tab._set_search_state(SearchUiState.SEARCHING)
        assert tab._search_btn.isEnabled() is False
        assert tab._connect_btn.isEnabled() is False

    def test_has_result_no_selection_connect_disabled(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        assert tab._connect_btn.isEnabled() is False

    def test_has_result_selected_normal_connect_enabled(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        _select_row(tab)
        assert tab._connect_btn.isEnabled() is True

    def test_minimized_selection_connect_disabled(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info(is_minimized=True)])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        _select_row(tab)
        assert tab._connect_btn.isEnabled() is False

    def test_connecting_disables_all_actions(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTING)
        assert tab._search_input.isEnabled() is False
        assert tab._search_btn.isEnabled() is False
        assert tab._connect_btn.isEnabled() is False
        assert tab._disconnect_btn.isEnabled() is False
        assert tab._start_executor_button.isEnabled() is False

    def test_connected_ready_enables_disconnect_and_execute(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        assert tab._disconnect_btn.isEnabled() is True
        assert tab._executor_state == ExecutorRunState.READY
        assert tab._start_executor_button.isEnabled() is True

    def test_connected_not_ready_execute_disabled(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_NOT_READY)
        assert tab._disconnect_btn.isEnabled() is True
        assert tab._executor_state == ExecutorRunState.NOT_READY
        assert tab._start_executor_button.isEnabled() is False

    def test_connected_unhealthy_execute_disabled(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_UNHEALTHY)
        assert tab._disconnect_btn.isEnabled() is True
        assert tab._executor_state == ExecutorRunState.NOT_READY
        assert tab._start_executor_button.isEnabled() is False

    def test_after_disconnect_with_selection_connect_enabled(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        _select_row(tab)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._do_disconnect()
        assert tab._connection_state == ConnectionUiState.DISCONNECTED
        assert tab._connect_btn.isEnabled() is True


class TestSwitchConnection:
    def test_connected_click_connect_shows_confirm(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        _select_row(tab)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as mock_q:
            tab._on_connect()
            mock_q.assert_called_once()

    def test_cancel_switch_keeps_state(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        _select_row(tab)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            tab._on_connect()

        assert tab._connection_state == ConnectionUiState.CONNECTED_READY
        assert tab._task_runner.connect_calls == []

    def test_confirm_switch_disconnects_and_connects(self, tab: GameConnectTab) -> None:
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.HAS_RESULT)
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        _select_row(tab)
        gen_before = tab._connection_generation

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            tab._on_connect()

        tab._window_manager.disconnect_window.assert_called_once()
        assert tab._connection_state == ConnectionUiState.CONNECTING
        assert tab._connection_generation == gen_before + 1
        assert len(tab._task_runner.connect_calls) == 1

    def test_switch_failure_disconnected(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 1
        tab._connect_request_generations[1] = 1
        tab._connecting = True
        tab._on_connect_failed(1, "fail")
        assert tab._connection_state == ConnectionUiState.DISCONNECTED


class TestDualStateCoexistence:
    def test_connected_while_searching(self, tab: GameConnectTab) -> None:
        tab._set_connection_state(ConnectionUiState.CONNECTED_READY)
        tab._fill_search_results([_fake_window_info()])
        tab._set_search_state(SearchUiState.SEARCHING)
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY
        assert tab._search_state == SearchUiState.SEARCHING
        assert tab._disconnect_btn.isEnabled() is True
        assert tab._connect_btn.isEnabled() is False
