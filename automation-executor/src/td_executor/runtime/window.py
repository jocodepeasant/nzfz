"""游戏窗口定位。"""

from __future__ import annotations

import sys
import logging
from ctypes import wintypes
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowRect:
    hwnd: int
    left: int
    top: int
    width: int
    height: int
    title: str = ""

    def __str__(self) -> str:
        t = f", title='{self.title}'" if self.title else ""
        return f"WindowRect(hwnd={self.hwnd}, left={self.left}, top={self.top}, {self.width}x{self.height}{t})"


def find_game_window(title_keyword: str = "逆战") -> WindowRect | None:
    if sys.platform == "win32":
        return _find_game_window_win(title_keyword)
    return _find_game_window_fallback(title_keyword)


def focus_window(hwnd: int) -> bool:
    if sys.platform == "win32":
        return _focus_window_win(hwnd)
    return _focus_window_fallback(hwnd)


def get_window_rect(hwnd: int) -> WindowRect | None:
    if sys.platform == "win32":
        return _get_window_rect_win(hwnd)
    return _get_window_rect_fallback(hwnd)


def is_window_valid(hwnd: int) -> bool:
    if sys.platform == "win32":
        return _is_window_valid_win(hwnd)
    return _is_window_valid_fallback(hwnd)


def list_windows(title_keyword: str = "") -> list[dict]:
    windows = _list_windows_win()
    if not title_keyword:
        return windows
    keyword = title_keyword.lower()
    return [w for w in windows if keyword in w["title"].lower()]


if sys.platform == "win32":
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    SW_RESTORE = 9

    def _find_game_window_win(title_keyword: str) -> WindowRect | None:
        matched: list[tuple[int, str]] = []

        def _enum_cb(hwnd: int, _lparam: int) -> int:
            if not user32.IsWindowVisible(hwnd):
                return 1
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return 1
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            text = buf.value
            if title_keyword.lower() in text.lower():
                matched.append((hwnd, text))
            return 1

        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

        if not matched:
            logger.warning("未找到标题包含 '%s' 的游戏窗口", title_keyword)
            return None

        hwnd, title = matched[0]
        rect = _get_window_rect_win(hwnd)
        if rect is not None:
            rect.title = title
        return rect

    def _focus_window_win(hwnd: int) -> bool:
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            logger.exception("聚焦窗口失败")
            return False

    def _get_window_rect_win(hwnd: int) -> WindowRect | None:
        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        try:
            rect = RECT()
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return None
            pt = POINT(rect.left, rect.top)
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
            return WindowRect(hwnd=hwnd, left=pt.x, top=pt.y, width=width, height=height, title=title)
        except Exception:
            return None

    def _is_window_valid_win(hwnd: int) -> bool:
        return bool(user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd))

    def _list_windows_win() -> list[dict]:
        result: list[dict] = []

        def _enum_cb(hwnd: int, _lparam: int) -> int:
            if not user32.IsWindowVisible(hwnd):
                return 1
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return 1
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            result.append({"hwnd": hwnd, "title": buf.value})
            return 1

        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        return result

else:

    def _find_game_window_win(title_keyword: str) -> WindowRect | None:
        return None

    def _focus_window_win(hwnd: int) -> bool:
        return False

    def _get_window_rect_win(hwnd: int) -> WindowRect | None:
        return None

    def _is_window_valid_win(hwnd: int) -> bool:
        return False

    def _list_windows_win() -> list[dict]:
        return []


def _find_game_window_fallback(title_keyword: str) -> WindowRect | None:
    logger.warning("非 Windows 平台，窗口定位功能受限，使用全屏区域作为降级方案")
    try:
        import mss

        monitor = mss.mss().monitors[0]
        return WindowRect(hwnd=0, left=monitor["left"], top=monitor["top"], width=monitor["width"], height=monitor["height"])
    except ImportError:
        return WindowRect(hwnd=0, left=0, top=0, width=1920, height=1080)


def _focus_window_fallback(hwnd: int) -> bool:
    logger.warning("非 Windows 平台，focus_window 不可用")
    return False


def _get_window_rect_fallback(hwnd: int) -> WindowRect | None:
    try:
        import mss

        monitor = mss.mss().monitors[0]
        return WindowRect(hwnd=0, left=monitor["left"], top=monitor["top"], width=monitor["width"], height=monitor["height"])
    except ImportError:
        return WindowRect(hwnd=0, left=0, top=0, width=1920, height=1080)


def _is_window_valid_fallback(hwnd: int) -> bool:
    return True
