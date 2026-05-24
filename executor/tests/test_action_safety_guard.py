"""P2-08 ActionSafetyGuard 单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import ClickAction, ScreenPoint
from nzfz_executor.core.actions.safety import ActionSafetyGuard
from nzfz_executor.core.models import ConnectedWindow, WindowRect


def _connected(window_rect: WindowRect) -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=1,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=window_rect,
        client_rect=window_rect,
    )


def _click(x: int, y: int) -> ClickAction:
    return ClickAction(point=ScreenPoint(x=x, y=y))


class TestActionSafetyGuard:
    def test_context_none_is_invalid(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(_click(10, 10), None)

        assert result.valid is False
        assert "连接上下文为空" in result.message

    def test_point_inside_window(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(150, 250),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is True

    def test_point_on_left_boundary(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(100, 250),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is True

    def test_point_on_top_boundary(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(150, 200),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is True

    def test_point_equal_right_is_invalid(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(900, 250),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is False

    def test_point_equal_bottom_is_invalid(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(150, 800),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is False

    def test_point_outside_window(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(50, 50),
            _connected(WindowRect(100, 200, 900, 800)),
        )

        assert result.valid is False

    def test_negative_window_origin_inside_point(self) -> None:
        guard = ActionSafetyGuard()
        result = guard.validate_click(
            _click(-95, -45),
            _connected(WindowRect(-100, -50, 700, 550)),
        )

        assert result.valid is True
