"""P1-02 UI Worker 与 TaskRunner 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nzfz_executor.core.models import (
    ConnectOptions,
    ConnectResult,
    ConnectedWindow,
    HealthCheckResult,
    HealthStatus,
    WindowInfo,
    WindowRect,
)
from nzfz_executor.core.window_manager import WindowManager
from nzfz_executor.ui.workers.window_task_runner import WindowTaskRunner
from nzfz_executor.ui.workers.window_workers import (
    WindowConnectWorker,
    WindowHealthCheckWorker,
    WindowSearchWorker,
)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


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


def _fake_connected_window() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


def _process_events_until(qapp, timeout_ms: int = 3000) -> None:
    from PySide6.QtCore import QElapsedTimer, QEventLoop

    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < timeout_ms:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)


class TestWindowSearchWorker:
    def test_search_finished_with_results(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        expected = [_fake_window_info()]
        manager.search_windows.return_value = expected
        received: list[tuple[int, list]] = []

        worker = WindowSearchWorker(7, manager, "逆战")
        worker.finished.connect(lambda rid, results: received.append((rid, results)))
        worker.run()

        assert received == [(7, expected)]
        manager.search_windows.assert_called_once_with("逆战")

    def test_search_finished_with_empty_results(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.search_windows.return_value = []
        received: list[tuple[int, list]] = []

        worker = WindowSearchWorker(1, manager, "none")
        worker.finished.connect(lambda rid, results: received.append((rid, results)))
        worker.run()

        assert received == [(1, [])]

    def test_search_failed_on_exception(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.search_windows.side_effect = RuntimeError("boom")
        received: list[tuple[int, str]] = []

        worker = WindowSearchWorker(2, manager, "x")
        worker.failed.connect(lambda rid, msg: received.append((rid, msg)))
        worker.run()

        assert received[0][0] == 2
        assert "任务执行异常" in received[0][1]


class TestWindowConnectWorker:
    def test_connect_finished_on_success(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        connected = _fake_connected_window()
        result = ConnectResult.ok(connected, activated=False)
        manager.connect_window.return_value = result
        received: list[tuple[int, ConnectResult]] = []

        worker = WindowConnectWorker(
            3,
            manager,
            _fake_window_info(),
            ConnectOptions(activate_on_connect=False),
        )
        worker.finished.connect(lambda rid, res: received.append((rid, res)))
        worker.run()

        assert received[0][0] == 3
        assert received[0][1].success is True

    def test_connect_finished_on_business_failure(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.connect_window.return_value = ConnectResult.fail("已最小化")
        received: list[tuple[int, ConnectResult]] = []
        failed: list[tuple[int, str]] = []

        worker = WindowConnectWorker(
            4,
            manager,
            _fake_window_info(),
            ConnectOptions(),
        )
        worker.finished.connect(lambda rid, res: received.append((rid, res)))
        worker.failed.connect(lambda rid, msg: failed.append((rid, msg)))
        worker.run()

        assert len(received) == 1
        assert received[0][1].success is False
        assert failed == []

    def test_connect_failed_on_exception(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.connect_window.side_effect = RuntimeError("connect boom")
        received: list[tuple[int, str]] = []

        worker = WindowConnectWorker(
            5,
            manager,
            _fake_window_info(),
            ConnectOptions(),
        )
        worker.failed.connect(lambda rid, msg: received.append((rid, msg)))
        worker.run()

        assert received[0][0] == 5
        assert "任务执行异常" in received[0][1]


class TestWindowHealthCheckWorker:
    def test_health_finished_when_healthy(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        health = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="ok",
            window=_fake_connected_window(),
            is_foreground=True,
        )
        manager.check_health.return_value = health
        received: list[tuple[int, HealthCheckResult]] = []

        worker = WindowHealthCheckWorker(6, manager)
        worker.finished.connect(lambda rid, res: received.append((rid, res)))
        worker.run()

        assert received[0][0] == 6
        assert received[0][1].is_healthy is True

    def test_health_finished_when_unhealthy(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        health = HealthCheckResult(
            status=HealthStatus.WINDOW_MINIMIZED,
            message="最小化",
            window=_fake_connected_window(),
        )
        manager.check_health.return_value = health
        failed: list[tuple[int, str]] = []
        received: list[tuple[int, HealthCheckResult]] = []

        worker = WindowHealthCheckWorker(8, manager)
        worker.finished.connect(lambda rid, res: received.append((rid, res)))
        worker.failed.connect(lambda rid, msg: failed.append((rid, msg)))
        worker.run()

        assert len(received) == 1
        assert failed == []

    def test_health_failed_on_exception(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.check_health.side_effect = RuntimeError("health boom")
        received: list[tuple[int, str]] = []

        worker = WindowHealthCheckWorker(9, manager)
        worker.failed.connect(lambda rid, msg: received.append((rid, msg)))
        worker.run()

        assert received[0][0] == 9
        assert "任务执行异常" in received[0][1]


class TestWindowTaskRunner:
    def test_start_search_forwards_finished(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        expected = [_fake_window_info()]
        manager.search_windows.return_value = expected

        runner = WindowTaskRunner(manager)
        received: list[tuple[int, list]] = []
        runner.search_finished.connect(lambda rid, res: received.append((rid, res)))

        runner.start_search(11, "test")
        _process_events_until(qapp)

        assert received == [(11, expected)]
        assert runner._tasks == {}

    def test_start_search_forwards_failed(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        manager.search_windows.side_effect = RuntimeError("search fail")

        runner = WindowTaskRunner(manager)
        received: list[tuple[int, str]] = []
        runner.search_failed.connect(lambda rid, msg: received.append((rid, msg)))

        runner.start_search(12, "bad")
        _process_events_until(qapp)

        assert received[0][0] == 12
        assert "任务执行异常" in received[0][1]
        assert runner._tasks == {}

    def test_start_connect_forwards_finished(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        result = ConnectResult.ok(_fake_connected_window())
        manager.connect_window.return_value = result

        runner = WindowTaskRunner(manager)
        received: list[tuple[int, ConnectResult]] = []
        runner.connect_finished.connect(lambda rid, res: received.append((rid, res)))

        runner.start_connect(13, _fake_window_info(), ConnectOptions())
        _process_events_until(qapp)

        assert received[0][0] == 13
        assert received[0][1].success is True
        assert runner._tasks == {}

    def test_start_health_check_forwards_finished(self, qapp) -> None:
        manager = MagicMock(spec=WindowManager)
        health = HealthCheckResult(status=HealthStatus.HEALTHY, message="ok")
        manager.check_health.return_value = health

        runner = WindowTaskRunner(manager)
        received: list[tuple[int, HealthCheckResult]] = []
        runner.health_finished.connect(lambda rid, res: received.append((rid, res)))

        runner.start_health_check(14)
        _process_events_until(qapp)

        assert received[0][0] == 14
        assert received[0][1].is_healthy is True
        assert runner._tasks == {}
