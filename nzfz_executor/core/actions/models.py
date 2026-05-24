"""输入动作数据模型（P2-07）。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ScreenPoint:
    """屏幕坐标。"""

    x: int
    y: int


class MouseButton(str, Enum):
    """鼠标按钮。"""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass(frozen=True)
class ClickAction:
    """点击动作描述。"""

    point: ScreenPoint
    button: MouseButton = MouseButton.LEFT
    duration_ms: int = 50


@dataclass(frozen=True)
class ActionResult:
    """动作执行结果。"""

    success: bool
    message: str = ""
