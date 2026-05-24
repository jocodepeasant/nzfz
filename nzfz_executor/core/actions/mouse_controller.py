"""鼠标控制器（P2-08 backend 组合）。"""

from __future__ import annotations

from collections.abc import Callable

from nzfz_executor.core.actions.backends.base import MouseInputBackend
from nzfz_executor.core.actions.backends.dry_run_backend import DryRunMouseBackend
from nzfz_executor.core.actions.backends.send_input_backend import SendInputMouseBackend
from nzfz_executor.core.actions.foreground import warn_if_not_foreground
from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseDragAction,
)
from nzfz_executor.core.actions.safety import ActionSafetyGuard
from nzfz_executor.core.models import ConnectedWindow


class MouseController:
    """鼠标点击与拖拽控制器，通过输入后端执行动作。"""

    def __init__(
        self,
        backend: MouseInputBackend,
        safety_guard: ActionSafetyGuard | None = None,
    ) -> None:
        self._backend = backend
        self._safety_guard = safety_guard or ActionSafetyGuard()

    @classmethod
    def create_default(cls, dry_run: bool = True) -> MouseController:
        if dry_run:
            backend = DryRunMouseBackend()
        else:
            backend = SendInputMouseBackend()

        return cls(backend=backend)

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindow | None = None,
        log: Callable[[str], None] | None = None,
    ) -> ActionResult:
        warn_if_not_foreground(context, log)
        return self._backend.click(
            action=action,
            context=context,
        )

    def drag(
        self,
        action: MouseDragAction,
        context: ConnectedWindow | None = None,
        log: Callable[[str], None] | None = None,
    ) -> ActionResult:
        if context is None:
            return ActionResult(
                success=False,
                message="拖拽失败：未连接窗口",
            )

        validation = self._safety_guard.validate_drag(
            start=action.start,
            end=action.end,
            context=context,
        )
        if not validation.valid:
            return ActionResult(
                success=False,
                message=validation.message,
            )

        warn_if_not_foreground(context, log)
        return self._backend.drag(
            action=action,
            context=context,
        )
