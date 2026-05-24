"""动作安全校验（P2-08）。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import (
    ActionValidationResult,
    ClickAction,
    MouseDragAction,
    ScreenPoint,
)
from nzfz_executor.core.models import ConnectedWindow


class ActionSafetyGuard:
    """真实点击前的最小安全校验。"""

    def validate_click(
        self,
        action: ClickAction,
        context: ConnectedWindow | None,
    ) -> ActionValidationResult:
        if context is None:
            return ActionValidationResult(
                valid=False,
                message="动作安全校验失败：连接上下文为空",
            )

        rect = context.window_rect
        point = action.point

        if not (
            rect.left <= point.x < rect.right
            and rect.top <= point.y < rect.bottom
        ):
            return ActionValidationResult(
                valid=False,
                message=(
                    "动作安全校验失败：点击坐标超出连接窗口范围，"
                    f"point=({point.x},{point.y}), "
                    f"window=({rect.left},{rect.top},"
                    f"{rect.right},{rect.bottom})"
                ),
            )

        return ActionValidationResult(
            valid=True,
            message="动作安全校验通过",
        )

    def validate_drag(
        self,
        start: ScreenPoint,
        end: ScreenPoint,
        context: ConnectedWindow | None,
    ) -> ActionValidationResult:
        if context is None:
            return ActionValidationResult(
                valid=False,
                message="动作安全校验失败：连接上下文为空",
            )

        rect = context.window_rect
        for label, point in (("start", start), ("end", end)):
            if not (
                rect.left <= point.x < rect.right
                and rect.top <= point.y < rect.bottom
            ):
                return ActionValidationResult(
                    valid=False,
                    message=(
                        "动作安全校验失败：拖拽坐标超出连接窗口范围，"
                        f"{label}=({point.x},{point.y}), "
                        f"window=({rect.left},{rect.top},"
                        f"{rect.right},{rect.bottom})"
                    ),
                )

        return ActionValidationResult(
            valid=True,
            message="拖拽安全校验通过",
        )
