"""P1-03 游戏连接页请求防覆盖、防抖与超时控制测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.models import (
    ConnectResult,
    ConnectedWindow,
    HealthCheckResult,
    HealthStatus,
    WindowInfo,
    WindowRect,
)
from nzfz_executor.ui.tabs.game_connect import ConnectionUiState, GameConnectTab


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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


def _fake_window_info() -> WindowInfo:
    return WindowInfo(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        width=800,
        height=600,
        match_score=1.0,
    )


def _fake_connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


class TestRequestValidityHelpers:
    def test_is_connect_result_current(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 5
        tab._connection_generation = 2
        assert tab._is_connect_result_current(5, 2) is True
        assert tab._is_connect_result_current(4, 2) is False
        assert tab._is_connect_result_current(5, 1) is False

    def test_is_health_result_current(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 3
        tab._connection_generation = 1
        assert tab._is_health_result_current(3, 1) is True
        assert tab._is_health_result_current(2, 1) is False
        assert tab._is_health_result_current(3, 0) is False

    def test_invalidate_search(self, tab: GameConnectTab) -> None:
        tab._search_request_id = 2
        tab._active_search_request_id = 2
        tab._search_running = True
        tab._invalidate_search()
        assert tab._active_search_request_id == 3
        assert tab._search_running is False


class TestSearchRequestGuard:
    def test_stale_search_finished_ignored(self, tab: GameConnectTab) -> None:
        tab._active_search_request_id = 2
        tab._search_running = True
        tab._on_search_finished(1, [_fake_window_info()])
        assert tab._search_running is True
        assert tab._search_results == []

    def test_current_search_finished_updates(self, tab: GameConnectTab) -> None:
        info = _fake_window_info()
        tab._active_search_request_id = 1
        tab._search_running = True
        tab._on_search_finished(1, [info])
        assert tab._search_running is False
        assert len(tab._search_results) == 1

    def test_empty_keyword_invalidates_without_worker(self, tab: GameConnectTab) -> None:
        tab._search_request_id = 5
        tab._active_search_request_id = 5
        tab._search_results = [_fake_window_info()]
        tab._fill_search_results(tab._search_results)
        tab._handle_empty_keyword()
        assert tab._search_results == []
        assert tab._active_search_request_id == 6
        assert tab._task_runner.search_calls == []


class TestConnectionGeneration:
    def test_start_connect_increments_generation(self, tab: GameConnectTab) -> None:
        before = tab._connection_generation
        tab._start_connect(_fake_window_info())
        assert tab._connection_generation == before + 1
        assert tab._connecting is True
        assert tab._connect_request_generations[1] == tab._connection_generation

    def test_disconnect_increments_generation(self, tab: GameConnectTab) -> None:
        before = tab._connection_generation
        tab._do_disconnect()
        assert tab._connection_generation == before + 1
        assert tab._active_connect_request_id == 0
        assert tab._active_health_request_id == 0

    def test_stale_connect_success_triggers_disconnect(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 1
        tab._connection_generation = 2
        tab._connect_request_generations[1] = 1
        result = ConnectResult.ok(_fake_connected())
        tab._on_connect_finished(1, result)
        tab._window_manager.disconnect_window.assert_called_once()

    def test_connect_timeout_disconnects(self, tab: GameConnectTab) -> None:
        tab._active_connect_request_id = 7
        tab._connection_generation = 3
        tab._connect_request_generations[7] = 3
        tab._connecting = True
        tab._on_connect_timeout(7)
        tab._window_manager.disconnect_window.assert_called_once()
        assert tab._connecting is False
        assert tab._connection_state == ConnectionUiState.DISCONNECTED


class TestHealthRequestGuard:
    def test_stale_health_clears_running_but_not_state(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 2
        tab._health_request_generations[1] = 1
        tab._health_check_running = True
        tab._connection_state = ConnectionUiState.CONNECTED_READY

        health = HealthCheckResult(
            status=HealthStatus.HANDLE_INVALID,
            message="bad",
            window=_fake_connected(),
        )
        tab._on_health_finished(1, health)

        assert tab._health_check_running is False
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY

    def test_current_health_updates_ui(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 1
        tab._connection_generation = 1
        tab._health_request_generations[1] = 1
        tab._health_check_running = True
        tab._connection_state = ConnectionUiState.CONNECTED_READY

        health = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="ok",
            window=_fake_connected(),
            is_foreground=True,
        )
        tab._on_health_finished(1, health)

        assert tab._health_check_running is False
        assert tab._connection_state == ConnectionUiState.CONNECTED_READY
        assert "执行就绪" in tab._status_text.text()

    def test_health_timeout_clears_running_without_disconnect(self, tab: GameConnectTab) -> None:
        tab._active_health_request_id = 4
        tab._connection_generation = 1
        tab._health_request_generations[4] = 1
        tab._health_check_running = True
        tab._connection_state = ConnectionUiState.CONNECTED_READY
        gen_before = tab._connection_generation

        tab._on_health_timeout(4)

        assert tab._health_check_running is False
        assert tab._connection_generation == gen_before
        tab._window_manager.disconnect_window.assert_not_called()
        assert tab._connection_state == ConnectionUiState.CONNECTED_UNHEALTHY


class TestSearchDebounce:
    def test_text_changed_starts_debounce_not_immediate_search(self, tab: GameConnectTab) -> None:
        tab._search_input.setText("game")
        assert tab._search_debounce_timer.isActive()
        assert tab._task_runner.search_calls == []

    def test_immediate_search_stops_debounce_and_starts(self, tab: GameConnectTab) -> None:
        tab._search_input.setText("game")
        tab._trigger_immediate_search()
        assert not tab._search_debounce_timer.isActive()
        assert len(tab._task_runner.search_calls) == 1
        assert tab._task_runner.search_calls[0][1] == "game"
