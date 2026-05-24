"""P2-08 MouseController 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from nzfz_executor.core.actions.backends.dry_run_backend import DryRunMouseBackend
from nzfz_executor.core.actions.backends.send_input_backend import SendInputMouseBackend
from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseDragAction,
    ScreenPoint,
)
from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.models import ConnectedWindow, WindowRect


class TestMouseController:
    def test_create_default_true_uses_dry_run_backend(self) -> None:
        controller = MouseController.create_default(dry_run=True)

        assert isinstance(controller._backend, DryRunMouseBackend)

    def test_create_default_false_uses_send_input_backend(self) -> None:
        controller = MouseController.create_default(dry_run=False)

        assert isinstance(controller._backend, SendInputMouseBackend)

    def test_click_forwards_to_backend(self) -> None:
        backend = MagicMock()
        backend.click.return_value = ActionResult(success=True, message="ok")
        controller = MouseController(backend)

        action = ClickAction(point=ScreenPoint(x=1, y=2))
        result = controller.click(action, context=None)

        backend.click.assert_called_once_with(action=action, context=None)
        assert result.success is True

    def test_backend_failure_returned(self) -> None:
        backend = MagicMock()
        backend.click.return_value = ActionResult(success=False, message="failed")
        controller = MouseController(backend)

        result = controller.click(ClickAction(point=ScreenPoint(x=1, y=2)))

        assert result.success is False
        assert result.message == "failed"

    def test_dry_run_message_contains_dry_run(self) -> None:
        controller = MouseController.create_default(dry_run=True)
        result = controller.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert "dry-run" in result.message

    def test_drag_outside_window_fails(self) -> None:
        controller = MouseController.create_default(dry_run=True)
        context = ConnectedWindow(
            hwnd=1,
            title="Game",
            process_name="game.exe",
            pid=1,
            window_rect=WindowRect(0, 0, 100, 100),
            client_rect=WindowRect(0, 0, 100, 100),
        )
        result = controller.drag(
            MouseDragAction(
                start=ScreenPoint(x=50, y=50),
                end=ScreenPoint(x=150, y=50),
            ),
            context=context,
        )

        assert result.success is False
        assert "超出连接窗口范围" in result.message

    def test_dry_run_drag_message(self) -> None:
        controller = MouseController.create_default(dry_run=True)
        context = ConnectedWindow(
            hwnd=1,
            title="Game",
            process_name="game.exe",
            pid=1,
            window_rect=WindowRect(0, 0, 200, 200),
            client_rect=WindowRect(0, 0, 200, 200),
        )
        result = controller.drag(
            MouseDragAction(
                start=ScreenPoint(x=10, y=10),
                end=ScreenPoint(x=50, y=50),
                duration_ms=300,
            ),
            context=context,
        )

        assert result.success is True
        assert "[Mouse] dry-run drag" in result.message
