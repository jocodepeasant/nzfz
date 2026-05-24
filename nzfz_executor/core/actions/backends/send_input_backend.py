"""SendInput 鼠标输入后端（P2-08）。"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseButton,
)
from nzfz_executor.core.actions.safety import ActionSafetyGuard
from nzfz_executor.core.models import ConnectedWindow

INPUT_MOUSE = 0

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


_BUTTON_FLAGS = {
    MouseButton.LEFT: (
        MOUSEEVENTF_LEFTDOWN,
        MOUSEEVENTF_LEFTUP,
    ),
    MouseButton.RIGHT: (
        MOUSEEVENTF_RIGHTDOWN,
        MOUSEEVENTF_RIGHTUP,
    ),
    MouseButton.MIDDLE: (
        MOUSEEVENTF_MIDDLEDOWN,
        MOUSEEVENTF_MIDDLEUP,
    ),
}


class SendInputMouseBackend:
    """通过 SetCursorPos + SendInput 执行真实鼠标点击。"""

    def __init__(
        self,
        safety_guard: ActionSafetyGuard | None = None,
    ) -> None:
        self._safety_guard = safety_guard or ActionSafetyGuard()

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindow | None = None,
    ) -> ActionResult:
        validation = self._safety_guard.validate_click(
            action=action,
            context=context,
        )
        if not validation.valid:
            return ActionResult(
                success=False,
                message=validation.message,
            )

        point = action.point

        try:
            if not ctypes.windll.user32.SetCursorPos(
                int(point.x),
                int(point.y),
            ):
                return ActionResult(
                    success=False,
                    message="真实点击失败：SetCursorPos 调用失败",
                )

            down_flag, up_flag = self._get_button_flags(action.button)

            self._send_mouse_flag(down_flag)

            duration = max(0, action.duration_ms) / 1000
            if duration > 0:
                time.sleep(duration)

            self._send_mouse_flag(up_flag)

            return ActionResult(
                success=True,
                message=(
                    "真实点击完成 "
                    f"screen=({point.x},{point.y}), "
                    f"button={action.button.value}"
                ),
            )

        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"真实点击异常：{exc}",
            )

    def _get_button_flags(
        self,
        button: MouseButton,
    ) -> tuple[int, int]:
        if button not in _BUTTON_FLAGS:
            raise ValueError(f"不支持的鼠标按钮：{button}")

        return _BUTTON_FLAGS[button]

    def _send_mouse_flag(self, flag: int) -> None:
        input_struct = INPUT(
            type=INPUT_MOUSE,
            union=INPUT_UNION(
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=flag,
                    time=0,
                    dwExtraInfo=None,
                ),
            ),
        )

        sent = ctypes.windll.user32.SendInput(
            1,
            ctypes.byref(input_struct),
            ctypes.sizeof(INPUT),
        )

        if sent != 1:
            raise RuntimeError(f"SendInput 调用失败，sent={sent}")
