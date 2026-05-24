"""输入动作模块（P2-07/P2-08）。"""

from nzfz_executor.core.actions.backends import (
    DryRunMouseBackend,
    MouseInputBackend,
    SendInputMouseBackend,
)
from nzfz_executor.core.actions.models import (
    ActionResult,
    ActionValidationResult,
    ClickAction,
    MouseButton,
    ScreenPoint,
)
from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.actions.safety import ActionSafetyGuard

__all__ = [
    "ActionResult",
    "ActionSafetyGuard",
    "ActionValidationResult",
    "ClickAction",
    "DryRunMouseBackend",
    "MouseButton",
    "MouseController",
    "MouseInputBackend",
    "ScreenPoint",
    "SendInputMouseBackend",
]
