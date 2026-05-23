"""P2-05 ExecutorTaskRunner 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.models import ConnectedWindow, WindowRect
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

        assert runner.start(1, _fake_connected()) is True
        _process_events_until(qapp)

        assert completed == [1]
        assert runner.is_running() is False
        assert runner._thread is None

    def test_start_rejected_when_already_running(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr(
            "nzfz_executor.ui.workers.executor_workers.EXECUTOR_PLACEHOLDER_TOTAL_STEPS",
            1000,
        )
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        runner = ExecutorTaskRunner()
        rejected: list[tuple[int, str]] = []
        runner.start_rejected.connect(
            lambda eid, msg: rejected.append((eid, msg)),
        )

        assert runner.start(1, _fake_connected()) is True
        assert runner.start(2, _fake_connected()) is False
        assert rejected[0][0] == 2
        assert "已有任务" in rejected[0][1]

        runner.request_stop()
        _process_events_until(qapp)

    def test_request_stop_emits_stopped(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        runner = ExecutorTaskRunner()
        stopped: list[int] = []
        runner.stopped.connect(stopped.append)

        assert runner.start(3, _fake_connected()) is True
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

        assert runner.start(4, _fake_connected()) is True
        _process_events_until(qapp)

        terminate.assert_not_called()
