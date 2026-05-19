from __future__ import annotations

import queue
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from td_executor.ui.events import (
    ActionCompleteEvent,
    ActionStartEvent,
    ExecutionDoneEvent,
    WaveChangeEvent,
)
from td_executor.ui.executor_bridge import ExecutorBridge


class TestActionStartEvent:
    def test_creation(self) -> None:
        evt = ActionStartEvent(action_index=0, action_type="place_trap", action_name="放置陷阱A", wave=1)
        assert evt.action_index == 0
        assert evt.action_type == "place_trap"
        assert evt.action_name == "放置陷阱A"
        assert evt.wave == 1


class TestActionCompleteEvent:
    def test_success(self) -> None:
        evt = ActionCompleteEvent(
            action_index=0, action_type="place_trap", action_name="放置陷阱A",
            wave=1, success=True, skipped=False, retry_count=0, duration_ms=150.0,
        )
        assert evt.success is True
        assert evt.skipped is False
        assert evt.retry_count == 0
        assert evt.duration_ms == 150.0

    def test_failure(self) -> None:
        evt = ActionCompleteEvent(
            action_index=1, action_type="upgrade_trap", action_name="升级陷阱B",
            wave=2, success=False, skipped=False, retry_count=3,
            error_message="map not open", duration_ms=5000.0,
        )
        assert evt.success is False
        assert evt.error_message == "map not open"
        assert evt.retry_count == 3

    def test_skipped(self) -> None:
        evt = ActionCompleteEvent(
            action_index=2, action_type="place_trap", action_name="放置陷阱C",
            wave=1, success=False, skipped=True, retry_count=0, duration_ms=10.0,
        )
        assert evt.skipped is True


class TestWaveChangeEvent:
    def test_creation(self) -> None:
        evt = WaveChangeEvent(wave=3, total_waves=10, wave_action_count=5)
        assert evt.wave == 3
        assert evt.total_waves == 10
        assert evt.wave_action_count == 5


class TestExecutionDoneEvent:
    def test_completed(self) -> None:
        evt = ExecutionDoneEvent(
            result="completed", total_actions=20, success_count=18,
            fail_count=1, skip_count=1, duration_seconds=120.5,
        )
        assert evt.result == "completed"
        assert evt.total_actions == 20
        assert evt.success_count == 18

    def test_stopped(self) -> None:
        evt = ExecutionDoneEvent(result="stopped")
        assert evt.result == "stopped"


class TestExecutorBridge:
    def test_initial_state(self) -> None:
        bridge = ExecutorBridge()
        assert bridge.running is False
        assert bridge.stop_requested is False

    def test_get_event_empty(self) -> None:
        bridge = ExecutorBridge()
        assert bridge.get_event() is None

    def test_get_event_with_timeout(self) -> None:
        bridge = ExecutorBridge()
        assert bridge.get_event(timeout=0.01) is None

    def test_request_stop(self) -> None:
        bridge = ExecutorBridge()
        bridge.request_stop()
        assert bridge.stop_requested is True

    def test_reset(self) -> None:
        bridge = ExecutorBridge()
        bridge.request_stop()
        assert bridge.stop_requested is True
        bridge.reset()
        assert bridge.stop_requested is False

    def test_reset_clears_queue(self) -> None:
        bridge = ExecutorBridge()
        bridge._event_queue.put(ActionStartEvent(0, "log", "test", 1))
        bridge.reset()
        assert bridge.get_event() is None

    def test_start_execution_already_running(self) -> None:
        bridge = ExecutorBridge()
        bridge._running = True
        result = bridge.start_execution({})
        assert result is False

    def test_start_execution_starts_thread(self) -> None:
        bridge = ExecutorBridge()
        barrier = threading.Barrier(2, timeout=2)

        original_execute = bridge._execute_script

        def _slow_execute(*args, **kwargs):
            barrier.wait()
            original_execute(*args, **kwargs)

        with patch.object(bridge, "_execute_script", _slow_execute):
            result = bridge.start_execution({"script_id": "test"})
            assert result is True
            barrier.wait()
            assert bridge.running is True
            bridge.request_stop()
            time.sleep(0.3)

    def test_start_execution_on_done_callback(self) -> None:
        bridge = ExecutorBridge()
        callback = MagicMock()

        def _noop_execute(*args, **kwargs):
            pass

        with patch.object(bridge, "_execute_script", _noop_execute):
            bridge.start_execution({"script_id": "test"}, on_done=callback)
            time.sleep(0.5)
            callback.assert_called_once()

    @patch("td_executor.runtime.window.find_game_window", return_value=None)
    @patch.object(ExecutorBridge, "_save_report")
    def test_execute_script_no_window(self, mock_save: MagicMock, mock_find: MagicMock) -> None:
        bridge = ExecutorBridge()
        bridge._execute_script({}, "逆战", False)
        event = bridge.get_event()
        assert isinstance(event, ExecutionDoneEvent)
        assert event.result == "error"

    @patch("td_executor.engine.action.ActionExecutor")
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_execute_script_dry_run(self, mock_save: MagicMock, mock_find: MagicMock, mock_exec_cls: MagicMock) -> None:
        from td_executor.runtime.window import WindowRect
        mock_find.return_value = WindowRect(hwnd=1, left=0, top=0, width=1920, height=1080)
        mock_executor = MagicMock()
        mock_exec_cls.return_value = mock_executor

        script_data = {
            "script_id": "test",
            "script_name": "测试脚本",
            "waves": [
                {"wave": 1, "actions": [
                    {"type": "log", "name": "测试日志"},
                ]},
            ],
        }
        bridge = ExecutorBridge()
        bridge._execute_script(script_data, "逆战", dry_run=True)

        events = []
        while True:
            evt = bridge.get_event()
            if evt is None:
                break
            events.append(evt)

        assert len(events) == 4
        assert isinstance(events[0], WaveChangeEvent)
        assert isinstance(events[1], ActionStartEvent)
        assert isinstance(events[2], ActionCompleteEvent)
        assert isinstance(events[3], ExecutionDoneEvent)
        assert events[2].success is True
        assert events[3].result == "completed"
        mock_executor.execute.assert_not_called()

    @patch("td_executor.engine.action.ActionExecutor")
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_execute_script_with_stop(self, mock_save: MagicMock, mock_find: MagicMock, mock_exec_cls: MagicMock) -> None:
        from td_executor.runtime.window import WindowRect
        mock_find.return_value = WindowRect(hwnd=1, left=0, top=0, width=1920, height=1080)
        mock_executor = MagicMock()
        mock_exec_cls.return_value = mock_executor
        mock_executor.execute.return_value = {"success": True, "skipped": False}

        script_data = {
            "script_id": "test",
            "script_name": "测试脚本",
            "waves": [
                {"wave": 1, "actions": [
                    {"type": "place_trap", "name": "放置"},
                    {"type": "log", "name": "日志"},
                ]},
            ],
        }
        bridge = ExecutorBridge()
        bridge.request_stop()
        bridge._execute_script(script_data, "逆战", dry_run=False)

        events = []
        while True:
            evt = bridge.get_event()
            if evt is None:
                break
            events.append(evt)

        done_events = [e for e in events if isinstance(e, ExecutionDoneEvent)]
        assert len(done_events) == 1
        assert done_events[0].result == "stopped"

    @patch("td_executor.engine.action.ActionExecutor")
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_execute_script_with_window_rect(self, mock_save: MagicMock, mock_find: MagicMock, mock_exec_cls: MagicMock) -> None:
        from td_executor.runtime.window import WindowRect
        rect = WindowRect(hwnd=99, left=100, top=200, width=800, height=600)
        mock_executor = MagicMock()
        mock_exec_cls.return_value = mock_executor

        script_data = {
            "script_id": "test",
            "script_name": "测试脚本",
            "waves": [
                {"wave": 1, "actions": [
                    {"type": "log", "name": "测试"},
                ]},
            ],
        }
        bridge = ExecutorBridge()
        bridge._execute_script(script_data, "逆战", dry_run=True, window_rect=rect)

        mock_find.assert_not_called()

        events = []
        while True:
            evt = bridge.get_event()
            if evt is None:
                break
            events.append(evt)

        done_events = [e for e in events if isinstance(e, ExecutionDoneEvent)]
        assert len(done_events) == 1
        assert done_events[0].result == "completed"


class TestCLIGuiCommand:
    @patch("td_executor.ui.app.launch")
    def test_gui_command_calls_launch(self, mock_launch: MagicMock) -> None:
        from typer.testing import CliRunner
        from td_executor.cli import app
        mock_launch.return_value = None
        runner = CliRunner()
        result = runner.invoke(app, ["gui"])
        mock_launch.assert_called_once()


class TestListWindows:
    @patch("td_executor.runtime.window.sys")
    def test_list_windows_fallback_non_win32(self, mock_sys: MagicMock) -> None:
        mock_sys.platform = "linux"
        from td_executor.runtime.window import list_windows
        result = list_windows()
        assert result == []

    def test_list_windows_with_keyword(self) -> None:
        from td_executor.runtime.window import list_windows
        fake_windows = [
            {"hwnd": 1, "title": "逆战 - 游戏"},
            {"hwnd": 2, "title": "记事本"},
            {"hwnd": 3, "title": "逆战 - 大厅"},
        ]
        with patch("td_executor.runtime.window._list_windows_win", return_value=fake_windows):
            result = list_windows("逆战")
        assert len(result) == 2
        assert result[0]["hwnd"] == 1
        assert result[1]["hwnd"] == 3


class TestConnectWindowByHwnd:
    @patch("td_executor.runtime.window.get_window_rect")
    def test_connect_by_hwnd_success(self, mock_get_rect: MagicMock) -> None:
        from td_executor.runtime.window import WindowRect
        mock_get_rect.return_value = WindowRect(hwnd=42, left=100, top=200, width=800, height=600, title="测试窗口")
        bridge = ExecutorBridge()
        with patch("td_executor.ui.app.ExecutorBridge", return_value=bridge):
            from td_executor.ui.app import ExecutorApp
            with patch.object(ExecutorApp, "__init__", lambda self: None):
                app = ExecutorApp()
                app._window_rect = None
                app.set_window_info = MagicMock()
                app.preview_tab = MagicMock()
                app.focus_force = MagicMock()
                result = app.connect_window_by_hwnd(42)
        assert result is True
        assert app._window_rect is not None
        assert app._window_rect.hwnd == 42

    @patch("td_executor.runtime.window.get_window_rect", return_value=None)
    def test_connect_by_hwnd_not_found(self, mock_get_rect: MagicMock) -> None:
        bridge = ExecutorBridge()
        with patch("td_executor.ui.app.ExecutorBridge", return_value=bridge):
            from td_executor.ui.app import ExecutorApp
            with patch.object(ExecutorApp, "__init__", lambda self: None):
                app = ExecutorApp()
                app._window_rect = None
                app.set_window_info = MagicMock()
                app.preview_tab = MagicMock()
                app.focus_force = MagicMock()
                result = app.connect_window_by_hwnd(9999)
        assert result is False
        assert app._window_rect is None


class TestWindowOverlay:
    def test_overlay_noop_on_non_win32(self) -> None:
        from td_executor.runtime.overlay import WindowOverlay
        overlay = WindowOverlay()
        assert overlay.show(1) is True
        assert overlay.hide() is True
        overlay.draw_click_marker(100, 200)
        overlay.draw_key_info("o", hold_ms=800)

    def test_overlay_draw_methods_noop(self) -> None:
        from td_executor.runtime.overlay import WindowOverlay
        overlay = WindowOverlay()
        overlay.draw_click_marker(0, 0)
        overlay.draw_key_info("a")


class TestExecutorBridgeFocus:
    @patch("td_executor.runtime.window.is_window_valid", return_value=True)
    @patch("td_executor.engine.action.ActionExecutor")
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_is_window_valid_called_before_execution(self, mock_save, mock_find, mock_exec_cls, mock_valid):
        from td_executor.runtime.window import WindowRect
        mock_find.return_value = WindowRect(hwnd=42, left=0, top=0, width=1920, height=1080)
        mock_executor = MagicMock()
        mock_exec_cls.return_value = mock_executor
        mock_executor.execute.return_value = {"success": True, "skipped": False}
        script_data = {
            "script_id": "test", "script_name": "测试",
            "waves": [{"wave": 1, "actions": [{"type": "log", "name": "日志"}]}],
        }
        bridge = ExecutorBridge()
        bridge._execute_script(script_data, "逆战", dry_run=True)
        mock_valid.assert_called_with(42)

    @patch("td_executor.runtime.window.is_window_valid", return_value=False)
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_stops_when_window_invalid(self, mock_save, mock_find, mock_valid):
        from td_executor.runtime.window import WindowRect
        mock_find.return_value = WindowRect(hwnd=42, left=0, top=0, width=1920, height=1080)
        bridge = ExecutorBridge()
        bridge._execute_script(script_data={"script_id": "t", "script_name": "t", "waves": [{"wave": 1, "actions": []}]}, title_keyword="逆战", dry_run=True)
        events = []
        while True:
            evt = bridge.get_event()
            if evt is None:
                break
            events.append(evt)
        from td_executor.ui.events import ExecutionDoneEvent
        done = [e for e in events if isinstance(e, ExecutionDoneEvent)]
        assert len(done) == 1
        assert done[0].result == "error"

    @patch("td_executor.runtime.window.focus_window")
    @patch("td_executor.runtime.window.is_window_valid", return_value=True)
    @patch("td_executor.engine.action.ActionExecutor")
    @patch("td_executor.runtime.window.find_game_window")
    @patch.object(ExecutorBridge, "_save_report")
    def test_focus_window_not_called(self, mock_save, mock_find, mock_exec_cls, mock_valid, mock_focus):
        from td_executor.runtime.window import WindowRect
        mock_find.return_value = WindowRect(hwnd=42, left=0, top=0, width=1920, height=1080)
        mock_executor = MagicMock()
        mock_exec_cls.return_value = mock_executor
        mock_executor.execute.return_value = {"success": True, "skipped": False}
        script_data = {
            "script_id": "test", "script_name": "测试",
            "waves": [{"wave": 1, "actions": [{"type": "log", "name": "日志"}]}],
        }
        bridge = ExecutorBridge()
        bridge._execute_script(script_data, "逆战", dry_run=True)
        mock_focus.assert_not_called()


class TestDebugMode:
    def test_debug_var_default_false(self) -> None:
        pass

    def test_bridge_set_overlay(self) -> None:
        bridge = ExecutorBridge()
        assert bridge._overlay is None
        bridge.set_overlay("fake_overlay")
        assert bridge._overlay == "fake_overlay"
        bridge.set_overlay(None)
        assert bridge._overlay is None
