"""执行器单元测试。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nzfz_executor.actions import register_builtin_handlers
from nzfz_executor.actions.base import ActionRegistry, ActionResult
from nzfz_executor.conditions.base import ConditionRegistry
from nzfz_executor.conditions.evaluator import ConditionEvaluator
from nzfz_executor.config import ExecutorConfig
from nzfz_executor.context import ExecutionContext
from nzfz_executor.core.dispatcher import ActionDispatcher
from nzfz_executor.core.engine import ExecutorEngine
from nzfz_executor.core.models import ConnectedWindow, WindowInfo, WindowRect, ConnectOptions
from nzfz_executor.core.pipeline import ExecutionPipeline
from nzfz_executor.core.scheduler import WaveScheduler
from nzfz_executor.core.window_manager import WindowManager
from nzfz_executor.events import EventBus
from nzfz_executor.lifecycle import LifecycleManager
from nzfz_executor.retry.manager import RetryManager
from nzfz_executor.runtime.window import from_connected_window
from nzfz_executor.script.loader import ScriptLoader
from nzfz_executor.script.validator import ScriptValidator


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "tower_defense_script_v1.schema.json"
EXAMPLE_SCRIPT = REPO_ROOT / "schemas" / "examples" / "space_station_normal_baseline_v1.json"


def test_script_loader_loads_example_json() -> None:
    data = ScriptLoader().load(EXAMPLE_SCRIPT)
    assert data["game_mode"] == "tower_defense"
    assert "waves" in data


def test_script_validator_accepts_example_json() -> None:
    data = ScriptLoader().load(EXAMPLE_SCRIPT)
    errors = ScriptValidator(SCHEMA_PATH).validate(data)
    assert errors == []


def test_script_validator_rejects_invalid_json() -> None:
    errors = ScriptValidator(SCHEMA_PATH).validate({"schema_version": "1.0.0"})
    assert errors


def test_from_connected_window_maps_client_rect() -> None:
    connected = ConnectedWindow(
        hwnd=100,
        title="Test",
        process_name="test.exe",
        pid=1234,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(10, 20, 790, 580),
    )
    runtime_window = from_connected_window(connected)
    assert runtime_window.hwnd == 100
    assert runtime_window.left == 10
    assert runtime_window.top == 20
    assert runtime_window.width == 780
    assert runtime_window.height == 560


def test_execution_context_set_window_from_connected() -> None:
    connected = ConnectedWindow(
        hwnd=1,
        title="Game",
        process_name="game.exe",
        pid=99,
        window_rect=WindowRect(0, 0, 100, 100),
        client_rect=WindowRect(0, 0, 100, 100),
    )
    context = ExecutionContext()
    context.set_window_from_connected(connected)
    assert context.connected_window is connected
    assert context.window is not None
    assert context.window.title == "Game"


def test_dispatcher_runs_log_action() -> None:
    register_builtin_handlers()
    dispatcher = ActionDispatcher()
    context = ExecutionContext()
    result = dispatcher.dispatch({"type": "log", "message": "hello"}, context)
    assert result.success is True


def test_pipeline_runs_log_actions() -> None:
    register_builtin_handlers()
    event_bus = EventBus()
    pipeline = ExecutionPipeline(
        ActionDispatcher(),
        ConditionEvaluator(ConditionRegistry()),
        RetryManager(),
        event_bus,
    )
    context = ExecutionContext()
    results = pipeline.run(
        [{"type": "log", "message": "wave action"}],
        context,
    )
    assert len(results) == 1
    assert results[0].success is True


def test_engine_loads_and_runs_log_wave() -> None:
    register_builtin_handlers()
    config = ExecutorConfig(schema_path=SCHEMA_PATH)
    event_bus = EventBus()
    lifecycle = LifecycleManager(event_bus)
    engine = ExecutorEngine(config, event_bus, lifecycle)

    data = ScriptLoader().load(EXAMPLE_SCRIPT)
    data["waves"] = [
        {
            "wave": 1,
            "name": "test-wave",
            "execute_once": True,
            "trigger": {"type": "manual"},
            "actions": [{"type": "log", "message": "ok"}],
        }
    ]
    path = Path("test_script_engine.json")
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        engine.load_script(path)
        engine.start()
        assert lifecycle.state.value == "stopped"
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.skipif(not WindowManager().is_supported(), reason="需要 Windows + pywin32 + psutil")
def test_window_manager_connect_notepad_if_available() -> None:
    manager = WindowManager()
    results = manager.search_windows("notepad")
    if not results:
        pytest.skip("未找到 notepad 窗口")
    visible = [item for item in results if not item.is_minimized]
    if not visible:
        pytest.skip("notepad 窗口均已最小化")
    result = manager.connect_window(
        visible[0],
        ConnectOptions(activate_on_connect=False),
    )
    assert result.success is True
    assert result.activated is False
    assert manager.get_connected_window() is not None
    manager.disconnect_window()


@patch("nzfz_executor.core.window_manager.win32gui")
@patch("nzfz_executor.core.window_manager.win32process")
@patch("nzfz_executor.core.window_manager.psutil")
def test_build_connected_window_rejects_minimized(
    mock_psutil: MagicMock,
    mock_win32process: MagicMock,
    mock_win32gui: MagicMock,
) -> None:
    manager = WindowManager()
    window = WindowInfo(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        width=800,
        height=600,
        match_score=1.0,
    )
    mock_win32gui.IsWindow.return_value = True
    mock_win32gui.IsWindowVisible.return_value = True
    mock_win32gui.IsIconic.return_value = True

    ok, error, candidate = manager._build_connected_window(window)
    assert ok is False
    assert candidate is None
    assert "最小化" in error


@patch.object(WindowManager, "_activate_window")
@patch.object(WindowManager, "_build_connected_window")
@patch.object(WindowManager, "_validate_window_for_connect")
def test_connect_window_skips_activation_when_disabled(
    mock_validate: MagicMock,
    mock_build: MagicMock,
    mock_activate: MagicMock,
) -> None:
    manager = WindowManager()
    window = WindowInfo(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        width=800,
        height=600,
        match_score=1.0,
    )
    connected = ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )
    mock_validate.return_value = (True, "")
    mock_build.return_value = (True, "", connected)

    result = manager.connect_window(window, ConnectOptions(activate_on_connect=False))

    mock_activate.assert_not_called()
    assert result.success is True
    assert result.activated is False
    assert manager.get_connected_window() is connected
    manager.disconnect_window()


@patch.object(WindowManager, "_activate_window")
@patch.object(WindowManager, "_build_connected_window")
@patch.object(WindowManager, "_validate_window_for_connect")
def test_connect_window_activates_when_enabled(
    mock_validate: MagicMock,
    mock_build: MagicMock,
    mock_activate: MagicMock,
) -> None:
    manager = WindowManager()
    window = WindowInfo(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        width=800,
        height=600,
        match_score=1.0,
    )
    connected = ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )
    mock_validate.return_value = (True, "")
    mock_build.return_value = (True, "", connected)
    mock_activate.return_value = (True, "")

    result = manager.connect_window(window, ConnectOptions(activate_on_connect=True))

    mock_activate.assert_called_once_with(42)
    assert result.success is True
    assert result.activated is True
    manager.disconnect_window()


def _fake_connected_window() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


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


def test_window_manager_initial_state() -> None:
    manager = WindowManager()
    assert manager.is_connected() is False
    assert manager.connected_window is None
    assert manager.last_error is None
    assert manager.last_window_info is None


def test_disconnect_when_not_connected_is_idempotent() -> None:
    manager = WindowManager()
    manager.disconnect_window()
    assert manager.is_connected() is False
    assert manager.connected_window is None
    assert manager.last_error is None


def test_disconnect_clears_connected_window() -> None:
    manager = WindowManager()
    connected = _fake_connected_window()
    manager._connected_window = connected
    manager.disconnect_window()
    assert manager.is_connected() is False
    assert manager.connected_window is None


def test_disconnect_clears_last_error() -> None:
    manager = WindowManager()
    manager._last_error = "some error"
    manager.disconnect_window()
    assert manager.last_error is None


def test_disconnect_preserves_last_window_info() -> None:
    manager = WindowManager()
    info = _fake_window_info()
    manager._last_window_info = info
    manager._connected_window = _fake_connected_window()
    manager.disconnect_window()
    assert manager.connected_window is None
    assert manager.last_window_info is info


def test_disconnect_idempotent_three_times() -> None:
    manager = WindowManager()
    manager._connected_window = _fake_connected_window()
    manager.disconnect_window()
    manager.disconnect_window()
    manager.disconnect_window()
    assert manager.is_connected() is False
    assert manager.last_error is None


def test_is_connected_reflects_connected_window() -> None:
    manager = WindowManager()
    assert manager.is_connected() is False
    manager._connected_window = _fake_connected_window()
    assert manager.is_connected() is True
    assert manager.connected_window is manager._connected_window


@patch.object(WindowManager, "_validate_window_for_connect")
def test_connect_rejects_when_already_connected(mock_validate: MagicMock) -> None:
    manager = WindowManager()
    existing = _fake_connected_window()
    manager._connected_window = existing
    window = _fake_window_info()

    result = manager.connect_window(window)

    mock_validate.assert_not_called()
    assert result.success is False
    assert manager.connected_window is existing
    assert manager.last_error is not None
    assert "请先断开" in manager.last_error
