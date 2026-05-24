"""鼠标控制器（P2-07 dry-run）。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import ActionResult, ClickAction


class MouseController:
    """鼠标点击控制器；P2-07 默认 dry-run，不真实点击。"""

    def __init__(self, dry_run: bool = True) -> None:
        self._dry_run = dry_run

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def click(self, action: ClickAction) -> ActionResult:
        if self._dry_run:
            point = action.point
            return ActionResult(
                success=True,
                message=(
                    "dry-run：跳过真实点击 "
                    f"screen=({point.x},{point.y})"
                ),
            )

        return ActionResult(
            success=False,
            message="真实点击尚未实现",
        )
