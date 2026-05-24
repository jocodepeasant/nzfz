"""P2-07 动作模型单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseButton,
    ScreenPoint,
)


class TestActionModels:
    def test_screen_point(self) -> None:
        point = ScreenPoint(x=100, y=200)
        assert point.x == 100
        assert point.y == 200

    def test_click_action_default_button(self) -> None:
        action = ClickAction(point=ScreenPoint(x=1, y=2))
        assert action.button == MouseButton.LEFT

    def test_action_result_success(self) -> None:
        result = ActionResult(success=True, message="ok")
        assert result.success is True
