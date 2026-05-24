"""P2-07 ExecutorWorker ODA 流程单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PIL import Image

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, ScreenshotResult, WindowRect
from nzfz_executor.core.vision.models import ImagePoint, RecognitionResult, TargetCandidate
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
        window_rect=WindowRect(100, 200, 900, 800),
        client_rect=WindowRect(100, 200, 900, 800),
    )


def _success_screenshot(width: int = 100, height: int = 100) -> ScreenshotResult:
    return ScreenshotResult(
        success=True,
        image=Image.new("RGB", (width, height)),
        width=width,
        height=height,
    )


def _make_runtime_context(
    *,
    connected: ConnectedWindow | None = None,
    screenshot_manager: MagicMock | None = None,
    recognizer=None,
    mouse_controller: MouseController | None = None,
    max_iterations: int = 1,
    loop_interval_ms: int = 0,
) -> ExecutorRuntimeContext:
    manager = screenshot_manager or MagicMock()
    if screenshot_manager is None:
        manager.capture.return_value = _success_screenshot()

    return ExecutorRuntimeContext(
        connected_context=connected or _fake_connected(),
        screenshot_manager=manager,
        recognizer=recognizer or CenterPointRecognizer(),
        coordinate_mapper=CoordinateMapper(),
        mouse_controller=mouse_controller or MouseController.create_default(dry_run=True),
        max_iterations=max_iterations,
        loop_interval_ms=loop_interval_ms,
    )


class TestExecutorOdaWorker:
    def test_runtime_context_none_emits_failed(self, qapp) -> None:
        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(1, None, stop_token)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed == [(1, "执行上下文为空，无法执行任务")]

    def test_normal_run_emits_completed(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        completed: list[int] = []
        logs: list[str] = []

        worker = ExecutorWorker(2, _make_runtime_context(), stop_token)
        worker.completed.connect(completed.append)
        worker.log.connect(lambda _eid, msg: logs.append(msg))
        worker.run()

        assert completed == [2]
        assert any("截图成功" in msg for msg in logs)
        assert any("识别到目标" in msg for msg in logs)
        assert any("dry-run" in msg for msg in logs)

    def test_max_iterations_three(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        logs: list[str] = []

        worker = ExecutorWorker(
            3,
            _make_runtime_context(max_iterations=3),
            stop_token,
        )
        worker.log.connect(lambda _eid, msg: logs.append(msg))
        worker.run()

        assert sum("开始第" in msg for msg in logs) == 3

    def test_not_found_does_not_fail(self, qapp) -> None:
        class EmptyRecognizer:
            def recognize(self, image: Image.Image) -> RecognitionResult:
                return RecognitionResult(found=False, candidates=[], message="未识别到目标")

        stop_token = StopToken()
        completed: list[int] = []
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            4,
            _make_runtime_context(recognizer=EmptyRecognizer()),
            stop_token,
        )
        worker.completed.connect(completed.append)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert completed == [4]
        assert failed == []

    def test_screenshot_failure_emits_failed(self, qapp) -> None:
        manager = MagicMock()
        manager.capture.return_value = ScreenshotResult(
            success=False,
            message="capture failed",
        )

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(5, _make_runtime_context(screenshot_manager=manager), stop_token)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed[0][0] == 5
        assert "截图失败" in failed[0][1]

    def test_recognizer_exception_emits_failed(self, qapp) -> None:
        class BoomRecognizer:
            def recognize(self, image: Image.Image) -> RecognitionResult:
                raise RuntimeError("recognize boom")

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            6,
            _make_runtime_context(recognizer=BoomRecognizer()),
            stop_token,
        )
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed == [(6, "recognize boom")]

    def test_mapper_exception_emits_failed(self, qapp) -> None:
        class BoomMapper:
            def image_to_screen(self, context, point: ImagePoint):
                raise RuntimeError("map boom")

        ctx = _make_runtime_context()
        ctx.coordinate_mapper = BoomMapper()

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(7, ctx, stop_token)
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed == [(7, "map boom")]

    def test_non_dry_run_action_emits_failed(self, qapp) -> None:
        from unittest.mock import MagicMock

        from nzfz_executor.core.actions.models import ActionResult

        mock_backend = MagicMock()
        mock_backend.click.return_value = ActionResult(
            success=False,
            message="真实点击失败：SetCursorPos 调用失败",
        )

        stop_token = StopToken()
        failed: list[tuple[int, str]] = []

        worker = ExecutorWorker(
            8,
            _make_runtime_context(
                mouse_controller=MouseController(mock_backend),
            ),
            stop_token,
        )
        worker.failed.connect(lambda eid, msg: failed.append((eid, msg)))
        worker.run()

        assert failed[0][0] == 8
        assert "真实点击失败" in failed[0][1]

    def test_stop_before_start_emits_stopped(self, qapp) -> None:
        stop_token = StopToken()
        stop_token.request_stop()
        stopped: list[int] = []

        worker = ExecutorWorker(9, _make_runtime_context(), stop_token)
        worker.stopped.connect(stopped.append)
        worker.run()

        assert stopped == [9]

    def test_stop_after_screenshot_emits_stopped(self, qapp) -> None:
        stop_token = StopToken()
        stopped: list[int] = []

        worker = ExecutorWorker(10, _make_runtime_context(), stop_token)
        worker.stopped.connect(stopped.append)

        def stop_on_screenshot(_execution_id: int, message: str) -> None:
            if message == "正在截图...":
                stop_token.request_stop()

        worker.log.connect(stop_on_screenshot)
        worker.run()

        assert stopped == [10]

    def test_stop_after_recognition_emits_stopped(self, qapp) -> None:
        stop_token = StopToken()
        stopped: list[int] = []

        worker = ExecutorWorker(11, _make_runtime_context(), stop_token)
        worker.stopped.connect(stopped.append)

        def stop_on_recognition(_execution_id: int, message: str) -> None:
            if message == "正在识别目标...":
                stop_token.request_stop()

        worker.log.connect(stop_on_recognition)
        worker.run()

        assert stopped == [11]

    def test_emits_progress_and_log(self, qapp, monkeypatch) -> None:
        monkeypatch.setattr("nzfz_executor.ui.workers.executor_workers.time.sleep", lambda _: None)

        stop_token = StopToken()
        progress: list[tuple[int, int, str]] = []
        logs: list[tuple[int, str]] = []

        worker = ExecutorWorker(12, _make_runtime_context(), stop_token)
        worker.progress.connect(
            lambda eid, percent, msg: progress.append((eid, percent, msg)),
        )
        worker.log.connect(lambda eid, msg: logs.append((eid, msg)))
        worker.run()

        assert progress
        assert logs
        assert progress[-1][1] == 100
