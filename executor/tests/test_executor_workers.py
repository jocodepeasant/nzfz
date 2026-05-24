"""P2-07 ExecutorWorker 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PIL import Image

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, ScreenshotResult, WindowRect
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.ui.workers.executor_workers import ExecutorWorker
from nzfz_executor.ui.workers.stop_token import StopToken


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
    manager = MagicMock()
    manager.capture.return_value = ScreenshotResult(
        success=True,
        image=Image.new("RGB", (100, 100)),
        width=100,
        height=100,
    )
    return ExecutorRuntimeContext(
        connected_context=kwargs.get("connected", _fake_connected()),
        screenshot_manager=manager,
        recognizer=CenterPointRecognizer(),
        coordinate_mapper=CoordinateMapper(),
        mouse_controller=MouseController.create_default(dry_run=True),
        max_iterations=kwargs.get("max_iterations", 1),
        loop_interval_ms=kwargs.get("loop_interval_ms", 0),
    )


class TestExecutorWorker:
    def test_runtime_context_none_emits_failed(self, qapp) -> None:
        stop_token = StopToken()
        received: list[tuple[int, str]] = []

        worker = ExecutorWorker(1, None, stop_token)
        worker.failed.connect(lambda eid, msg: received.append((eid, msg)))
        worker.run()

        assert received == [(1, "执行上下文为空，无法执行任务")]

    def test_normal_run_emits_completed_and_progress(
        self,
        qapp,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        completed: list[int] = []
        progress: list[tuple[int, int, str]] = []
        logs: list[tuple[int, str]] = []

        worker = ExecutorWorker(2, _make_runtime_context(), stop_token)
        worker.completed.connect(completed.append)
        worker.progress.connect(
            lambda eid, percent, msg: progress.append((eid, percent, msg)),
        )
        worker.log.connect(lambda eid, msg: logs.append((eid, msg)))
        worker.run()

        assert completed == [2]
        assert progress[-1][1] == 100
        assert logs[0] == (2, "执行任务已启动")
        assert logs[-1] == (2, "执行任务已完成")

    def test_stop_requested_emits_stopped(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        stopped: list[int] = []

        worker = ExecutorWorker(3, _make_runtime_context(), stop_token)
        worker.stopped.connect(stopped.append)

        def request_stop_on_first_log(execution_id: int, message: str) -> None:
            if message == "正在截图...":
                stop_token.request_stop()

        worker.log.connect(request_stop_on_first_log)
        worker.run()

        assert stopped == [3]

    def test_exception_emits_failed(self, qapp) -> None:
        manager = MagicMock()
        manager.capture.side_effect = RuntimeError("boom")

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        ctx = _make_runtime_context()
        ctx.screenshot_manager = manager

        worker = ExecutorWorker(4, ctx, stop_token)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed == [(4, "boom")]
