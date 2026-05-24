"""P2-07 ExecutorTaskRunner 单元测试。"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest
from PIL import Image

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, ScreenshotResult, WindowRect
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.ui.workers.executor_task_runner import ExecutorTaskRunner


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


def _make_runtime_context(*, block: threading.Event | None = None) -> ExecutorRuntimeContext:
    manager = MagicMock()

    def capture(*args, **kwargs):
        if block is not None:
            block.wait(timeout=30)
        return ScreenshotResult(
            success=True,
            image=Image.new("RGB", (100, 100)),
            width=100,
            height=100,
        )

    manager.capture.side_effect = capture

    return ExecutorRuntimeContext(
        connected_context=_fake_connected(),
        screenshot_manager=manager,
        recognizer=CenterPointRecognizer(),
        coordinate_mapper=CoordinateMapper(),
        mouse_controller=MouseController.create_default(dry_run=True),
        max_iterations=1,
        loop_interval_ms=0,
    )


def _process_events_until(qapp, timeout_ms: int = 5000) -> None:
    from PySide6.QtCore import QElapsedTimer, QEventLoop

    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < timeout_ms:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if not qapp.thread().isRunning():
            break


class TestExecutorTaskRunner:
    def test_start_forwards_completed(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        runner = ExecutorTaskRunner()
        completed: list[int] = []
        runner.completed.connect(completed.append)

        assert runner.start(1, _make_runtime_context()) is True
        _process_events_until(qapp)

        assert completed == [1]
        assert runner.is_running() is False
        assert runner._thread is None

    def test_start_rejected_when_already_running(self, qapp) -> None:
        block = threading.Event()
        runner = ExecutorTaskRunner()
        rejected: list[tuple[int, str]] = []
        runner.start_rejected.connect(
            lambda eid, msg: rejected.append((eid, msg)),
        )

        assert runner.start(1, _make_runtime_context(block=block)) is True
        assert runner.start(2, _make_runtime_context()) is False
        assert rejected[0][0] == 2
        assert "已有任务" in rejected[0][1]

        block.set()
        runner.request_stop()
        _process_events_until(qapp)

    def test_request_stop_emits_stopped(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        runner = ExecutorTaskRunner()
        stopped: list[int] = []
        runner.stopped.connect(stopped.append)

        assert runner.start(3, _make_runtime_context()) is True
        assert runner.request_stop() is True
        _process_events_until(qapp)

        assert stopped == [3]

    def test_request_stop_without_task_returns_false(self, qapp) -> None:
        runner = ExecutorTaskRunner()
        assert runner.request_stop() is False

    def test_does_not_call_thread_terminate(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        runner = ExecutorTaskRunner()
        original_thread = __import__(
            "PySide6.QtCore",
            fromlist=["QThread"],
        ).QThread

        terminate = MagicMock()
        monkeypatch.setattr(original_thread, "terminate", terminate)

        assert runner.start(4, _make_runtime_context()) is True
        _process_events_until(qapp)

        terminate.assert_not_called()
