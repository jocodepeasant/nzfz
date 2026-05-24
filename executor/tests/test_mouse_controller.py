"""P2-07 MouseController 单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import ClickAction, ScreenPoint
from nzfz_executor.core.actions.mouse_controller import MouseController


class TestMouseController:
    def test_dry_run_click_success(self) -> None:
        controller = MouseController(dry_run=True)
        result = controller.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert result.success is True

    def test_dry_run_does_not_perform_real_click(self) -> None:
        controller = MouseController(dry_run=True)
        assert controller.dry_run is True

    def test_dry_run_message_contains_dry_run(self) -> None:
        controller = MouseController(dry_run=True)
        result = controller.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert "dry-run" in result.message

    def test_non_dry_run_returns_failure(self) -> None:
        controller = MouseController(dry_run=False)
        result = controller.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert result.success is False

    def test_non_dry_run_message_not_implemented(self) -> None:
        controller = MouseController(dry_run=False)
        result = controller.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert result.message == "真实点击尚未实现"
