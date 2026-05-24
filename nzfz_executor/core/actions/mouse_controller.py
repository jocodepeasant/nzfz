"""鼠标控制器（P2-08 backend 组合）。"""

from __future__ import annotations

from nzfz_executor.core.actions.backends.base import MouseInputBackend
from nzfz_executor.core.actions.backends.dry_run_backend import DryRunMouseBackend
from nzfz_executor.core.actions.backends.send_input_backend import SendInputMouseBackend
from nzfz_executor.core.actions.models import ActionResult, ClickAction
from nzfz_executor.core.models import ConnectedWindow


class MouseController:
    """鼠标点击控制器，通过输入后端执行动作。"""

    def __init__(self, backend: MouseInputBackend) -> None:
        self._backend = backend

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
    ) -> ActionResult:
        return self._backend.click(
            action=action,
            context=context,
        )
