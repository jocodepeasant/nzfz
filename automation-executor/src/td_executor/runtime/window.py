"""游戏窗口定位与管理。"""

from dataclasses import dataclass

try:
    import win32gui
except ImportError:
    win32gui = None


@dataclass
class WindowRect:
    left: int
    top: int
    width: int
    height: int


class WindowManager:
    def __init__(self, window_title: str = "逆战：未来"):
        self.window_title = window_title
        self._handle = None

    def find_window(self) -> WindowRect:
        if win32gui is None:
            raise NotImplementedError("仅支持 Windows 平台")
        handle = win32gui.FindWindow(None, self.window_title)
        if not handle:
            raise RuntimeError("未找到游戏窗口，请先启动游戏")
        self._handle = handle
        left, top, right, bottom = win32gui.GetWindowRect(handle)
        return WindowRect(left=left, top=top, width=right - left, height=bottom - top)

    def bring_to_front(self) -> None:
        if win32gui is None:
            return
        if self._handle:
            win32gui.SetForegroundWindow(self._handle)

    def is_window_valid(self) -> bool:
        if win32gui is None:
            return True
        if not self._handle:
            return False
        return bool(win32gui.IsWindow(self._handle) and win32gui.IsWindowVisible(self._handle))
