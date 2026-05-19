from __future__ import annotations

import sys
import logging
import time

logger = logging.getLogger(__name__)

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
MK_LBUTTON = 0x0001


def MAKELPARAM(lo, hi):
    return (lo & 0xFFFF) | ((hi & 0xFFFF) << 16)


if sys.platform == "win32":
    import ctypes

    user32 = ctypes.windll.user32

    def _lparam_for_key(vk_code, is_keydown=True):
        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        repeat_count = 1
        extended_key = 0
        context_code = 0
        previous_state = 0 if is_keydown else 1
        transition_state = 0 if is_keydown else 1
        return (
            (repeat_count & 0xFFFF)
            | ((scan_code & 0xFF) << 16)
            | ((extended_key & 0x1) << 24)
            | ((context_code & 0x1) << 29)
            | ((previous_state & 0x1) << 30)
            | ((transition_state & 0x1) << 31)
        )

    def send_click(hwnd: int, x: int, y: int, button: str = "left") -> None:
        lparam = MAKELPARAM(x, y)
        if button == "right":
            user32.PostMessageW(hwnd, WM_RBUTTONDOWN, 1, lparam)
            user32.PostMessageW(hwnd, WM_RBUTTONUP, 0, lparam)
        else:
            user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    def send_key(hwnd: int, key: str, hold_ms: int = 0) -> None:
        vk_code = user32.VkKeyScanW(ord(key[0])) & 0xFF if len(key) == 1 else user32.VkKeyScanW(ord(key.upper()[0])) & 0xFF
        lparam_down = _lparam_for_key(vk_code, True)
        lparam_up = _lparam_for_key(vk_code, False)
        user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, lparam_down)
        if hold_ms > 0:
            time.sleep(hold_ms / 1000.0)
        user32.PostMessageW(hwnd, WM_KEYUP, vk_code, lparam_up)

else:

    def send_click(hwnd: int, x: int, y: int, button: str = "left") -> None:
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button)
        except ImportError:
            logger.warning("pyautogui 不可用，无法点击")

    def send_key(hwnd: int, key: str, hold_ms: int = 0) -> None:
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            resolved = key if len(key) == 1 else key
            kb.press(resolved)
            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)
            kb.release(resolved)
        except ImportError:
            logger.warning("pynput 不可用，无法按键")
