"""Dry-run 鼠标输入后端（P2-08）。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseDragAction,
)
from nzfz_executor.core.models import ConnectedWindow


class DryRunMouseBackend:
    """跳过真实点击，仅返回日志结果。"""

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindow | None = None,
    ) -> ActionResult:
        point = action.point

        return ActionResult(
            success=True,
            message=(
                "dry-run：跳过真实点击 "
                f"screen=({point.x},{point.y}), "
                f"button={action.button.value}"
            ),
        )

    def drag(
        self,
        action: MouseDragAction,
        context: ConnectedWindow | None = None,
    ) -> ActionResult:
        start = action.start
        end = action.end
        return ActionResult(
            success=True,
            message=(
                "[Mouse] dry-run drag "
                f"from=({start.x},{start.y}) to=({end.x},{end.y}), "
                f"duration={action.duration_ms}ms, "
                f"button={action.button.value}"
            ),
        )
