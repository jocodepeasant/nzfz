"""P2-05 ExecutorWorker 单元测试。"""

from __future__ import annotations

import pytest

from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.ui.workers.executor_workers import (
    EXECUTOR_PLACEHOLDER_TOTAL_STEPS,
    ExecutorWorker,
)
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


class TestExecutorWorker:
    def test_context_none_emits_failed(self, qapp) -> None:
        stop_token = StopToken()
        received: list[tuple[int, str]] = []

        worker = ExecutorWorker(1, None, stop_token)
        worker.failed.connect(lambda eid, msg: received.append((eid, msg)))
        worker.run()

        assert received == [(1, "当前未连接游戏窗口，无法执行任务")]

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

        worker = ExecutorWorker(2, _fake_connected(), stop_token)
        worker.completed.connect(completed.append)
        worker.progress.connect(
            lambda eid, percent, msg: progress.append((eid, percent, msg)),
        )
        worker.log.connect(lambda eid, msg: logs.append((eid, msg)))
        worker.run()

        assert completed == [2]
        assert len(progress) == EXECUTOR_PLACEHOLDER_TOTAL_STEPS
        assert progress[-1][1] == 100
        assert logs[0] == (2, "执行任务已启动")
        assert logs[-1] == (2, "执行任务已完成")

    def test_stop_requested_emits_stopped(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        stopped: list[int] = []

        worker = ExecutorWorker(3, _fake_connected(), stop_token)
        worker.stopped.connect(stopped.append)

        def request_stop_on_first_progress(
            execution_id: int,
            percent: int,
            message: str,
        ) -> None:
            if percent == 5:
                stop_token.request_stop()

        worker.progress.connect(request_stop_on_first_progress)
        worker.run()

        assert stopped == [3]

    def test_exception_emits_failed(self, qapp, monkeypatch) -> None:
        def boom(_seconds: float) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", boom)

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(4, _fake_connected(), stop_token)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed == [(4, "boom")]
