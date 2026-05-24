"""P2-07 ExecutorRuntimeContext 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from nzfz_executor.core.actions.keyboard_controller import KeyboardController
from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer


def _fake_connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=42,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


class TestExecutorRuntimeContext:
    def test_fields(self) -> None:
        ctx = ExecutorRuntimeContext(
            connected_context=_fake_connected(),
            screenshot_manager=MagicMock(),
            recognizer=CenterPointRecognizer(),
            coordinate_mapper=CoordinateMapper(),
            mouse_controller=MouseController.create_default(dry_run=True),
            keyboard_controller=KeyboardController.create_default(dry_run=True),
            max_iterations=1,
            loop_interval_ms=500,
        )

        assert ctx.connected_context.hwnd == 42
        assert ctx.max_iterations == 1
        assert ctx.loop_interval_ms == 500
        from nzfz_executor.core.actions.backends import DryRunMouseBackend

        assert isinstance(ctx.mouse_controller._backend, DryRunMouseBackend)
