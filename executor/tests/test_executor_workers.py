"""P2-10 ExecutorWorker 单元测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.options import ExecutorLaunchOptions
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.ui.config.defaults import DEFAULT_SCRIPT_PATH
from nzfz_executor.ui.workers.executor_workers import ExecutorWorker
from nzfz_executor.ui.workers.stop_token import StopToken

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _fake_connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


def _make_runtime_context(**kwargs) -> ExecutorRuntimeContext:
    return ExecutorRuntimeContext(
        connected_context=kwargs.get("connected", _fake_connected()),
        screenshot_manager=MagicMock(),
        recognizer=CenterPointRecognizer(),
        coordinate_mapper=CoordinateMapper(),
        mouse_controller=MouseController.create_default(dry_run=True),
        max_iterations=kwargs.get("max_iterations", 1),
        loop_interval_ms=kwargs.get("loop_interval_ms", 0),
    )


def _launch_options() -> ExecutorLaunchOptions:
    return ExecutorLaunchOptions(script_path=DEFAULT_SCRIPT_PATH)


class TestExecutorWorker:
    def test_runtime_context_none_emits_failed(self, qapp) -> None:
        stop_token = StopToken()
        received: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            1,
            None,
            _launch_options(),
            REPO_ROOT,
            stop_token,
        )
        worker.failed.connect(lambda eid, msg: received.append((eid, msg)))
        worker.run()

        assert received == [(1, "执行上下文为空，无法执行任务")]

    def test_normal_run_emits_completed(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.core.executor.script_executor.time.sleep", lambda _: None)

        stop_token = StopToken()
        completed: list[int] = []
        progress: list[tuple[int, int, str]] = []
        logs: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            2,
            _make_runtime_context(),
            _launch_options(),
            REPO_ROOT,
            stop_token,
        )
        worker.completed.connect(completed.append)
        worker.progress.connect(
            lambda eid, percent, msg: progress.append((eid, percent, msg)),
        )
        worker.log.connect(lambda eid, msg: logs.append((eid, msg)))
        worker.run()

        assert completed == [2]
        assert progress[-1][1] == 100
        assert any("[Script]" in msg for _, msg in logs)

    def test_missing_script_emits_failed(self, qapp) -> None:
        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            3,
            _make_runtime_context(),
            ExecutorLaunchOptions(script_path="resources/scripts/missing.json"),
            REPO_ROOT,
            stop_token,
        )
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed
        assert "不存在" in failed[0][1]
