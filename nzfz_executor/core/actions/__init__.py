"""输入动作模块（P2-07）。"""

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseButton,
    ScreenPoint,
)
from nzfz_executor.core.actions.mouse_controller import MouseController

__all__ = [
    "ActionResult",
    "ClickAction",
    "MouseButton",
    "MouseController",
    "ScreenPoint",
]
