"""鼠标输入后端协议（P2-08）。"""

from __future__ import annotations

from typing import Protocol

from nzfz_executor.core.actions.models import ActionResult, ClickAction
from nzfz_executor.core.models import ConnectedWindow


class MouseInputBackend(Protocol):
    """鼠标输入后端协议。"""

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindow | None = None,
    ) -> ActionResult:
        ...
