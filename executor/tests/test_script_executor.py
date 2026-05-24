"""P2-10 ScriptExecutor 测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.options import ExecutorLaunchOptions
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.executor.script_executor import (
    ScriptExecutor,
    ScriptExecutorCallbacks,
)
from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.core.scripts import ScriptLoader
from nzfz_executor.core.scripts.constants import SCRIPT_EXECUTION_MODE_SINGLE_WAVE
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.ui.config.defaults import DEFAULT_SCRIPT_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def default_script_bundle():
    result = ScriptLoader().load(REPO_ROOT / DEFAULT_SCRIPT_PATH)
    assert result.success
    assert result.script is not None
    assert result.indexes is not None
    return result.script, result.indexes


def _runtime_context() -> ExecutorRuntimeContext:
    return ExecutorRuntimeContext(
        connected_context=ConnectedWindow(
            hwnd=1,
            title="Game",
            process_name="game.exe",
            pid=1,
            window_rect=WindowRect(0, 0, 1920, 1080),
            client_rect=WindowRect(0, 0, 1920, 1080),
        ),
        screenshot_manager=MagicMock(),
        recognizer=CenterPointRecognizer(),
        coordinate_mapper=CoordinateMapper(),
        mouse_controller=MouseController.create_default(dry_run=True),
        max_iterations=1,
        loop_interval_ms=0,
    )


class TestScriptExecutor:
    def test_sequential_executes_enabled_actions(
        self,
        default_script_bundle,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr("nzfz_executor.core.executor.script_executor.time.sleep", lambda _: None)
        script, indexes = default_script_bundle
        logs: list[str] = []

        callbacks = ScriptExecutorCallbacks(
            log=logs.append,
            progress=lambda *_: None,
            is_stop_requested=lambda: False,
        )
        result = ScriptExecutor().execute(
            script=script,
            indexes=indexes,
            context=_runtime_context(),
            options=ExecutorLaunchOptions(script_path=DEFAULT_SCRIPT_PATH),
            callbacks=callbacks,
        )

        assert result.success is True
        assert any("[PlaceTrap]" in line for line in logs)
        assert any("disabled, skip" in line for line in logs)
        assert any("第1波初始布防完成" in line for line in logs)

    def test_single_wave_missing_fails(self, default_script_bundle) -> None:
        script, indexes = default_script_bundle
        result = ScriptExecutor().execute(
            script=script,
            indexes=indexes,
            context=_runtime_context(),
            options=ExecutorLaunchOptions(
                script_path=DEFAULT_SCRIPT_PATH,
                script_execution_mode=SCRIPT_EXECUTION_MODE_SINGLE_WAVE,
                script_single_wave=99,
            ),
            callbacks=ScriptExecutorCallbacks(
                log=lambda *_: None,
                progress=lambda *_: None,
                is_stop_requested=lambda: False,
            ),
        )

        assert result.success is False
        assert "未找到 wave=99" in result.message

    def test_ensure_region_cache(self, default_script_bundle, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.core.executor.script_executor.time.sleep", lambda _: None)
        script, indexes = default_script_bundle
        logs: list[str] = []

        ScriptExecutor().execute(
            script=script,
            indexes=indexes,
            context=_runtime_context(),
            options=ExecutorLaunchOptions(script_path=DEFAULT_SCRIPT_PATH),
            callbacks=ScriptExecutorCallbacks(
                log=logs.append,
                progress=lambda *_: None,
                is_stop_requested=lambda: False,
            ),
        )

        skip_logs = [line for line in logs if "跳过导航" in line]
        assert skip_logs
