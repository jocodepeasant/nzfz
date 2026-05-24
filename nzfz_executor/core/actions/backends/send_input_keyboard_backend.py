"""SendInput 键盘输入后端（P2-11）。"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

_VK_MAP: dict[str, int] = {
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "a": 0x41,
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,
    "esc": 0x1B,
    "space": 0x20,
    "enter": 0x0D,
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class KEYBOARD_INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
    ]


class KEYBOARD_INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", KEYBOARD_INPUT_UNION),
    ]


class SendInputKeyboardBackend:
    """通过 SendInput 执行真实按键。"""

    def press(self, key: str, hold_ms: int = 0) -> None:
        vk = _VK_MAP.get(key)
        if vk is None:
            raise ValueError(f"不支持的按键：{key}")

        self._send_key(vk, key_up=False)
        try:
            if hold_ms > 0:
                time.sleep(hold_ms / 1000)
        finally:
            self._send_key(vk, key_up=True)

    def _send_key(self, vk: int, key_up: bool) -> None:
        flags = KEYEVENTF_KEYUP if key_up else 0
        input_struct = KEYBOARD_INPUT(
            type=INPUT_KEYBOARD,
            union=KEYBOARD_INPUT_UNION(
                ki=KEYBDINPUT(
                    wVk=vk,
                    wScan=0,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=None,
                ),
            ),
        )
        sent = ctypes.windll.user32.SendInput(
            1,
            ctypes.byref(input_struct),
            ctypes.sizeof(KEYBOARD_INPUT),
        )
        if sent != 1:
            raise RuntimeError(f"SendInput 键盘调用失败，sent={sent}")
