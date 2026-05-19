"""游戏窗口定位。"""

from __future__ import annotations

import sys
import logging
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


def _find_game_window_win(title_keyword: str) -> WindowRect | None:
    try:
        import win32gui
    except ImportError:
        logger.error(
            "win32gui 不可用，无法定位游戏窗口。请安装 pywin32: pip install pywin32"
        )
        return None

    matched: list[tuple[int, str]] = []

    def _enum_cb(hwnd: int, _ctx: object) -> None:
        text = win32gui.GetWindowText(hwnd)
        if title_keyword.lower() in text.lower() and win32gui.IsWindowVisible(hwnd):
            matched.append((hwnd, text))

    win32gui.EnumWindows(_enum_cb, None)

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
        import win32gui
        import win32con
    except ImportError:
        logger.warning("win32gui 不可用，无法聚焦窗口")
        return False

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        logger.exception("聚焦窗口失败")
        return False


def _get_window_rect_win(hwnd: int) -> WindowRect | None:
    try:
        import win32gui
    except ImportError:
        return None

    try:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (left, top))
        width = right - left
        height = bottom - top
        title = win32gui.GetWindowText(hwnd)
        return WindowRect(hwnd=hwnd, left=screen_left, top=screen_top, width=width, height=height, title=title)
    except Exception:
        return None


def _is_window_valid_win(hwnd: int) -> bool:
    try:
        import win32gui
    except ImportError:
        return False

    return bool(win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd))


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
