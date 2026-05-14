from __future__ import annotations

from dataclasses import dataclass, field


class WindowNotFoundError(Exception):
    pass


class WindowMinimizedError(Exception):
    pass


@dataclass
class WindowRect:
    left: int
    top: int
    width: int
    height: int


@dataclass
class WindowManager:
    window_title: str = ""
    window_class: str = ""
    _rect: WindowRect | None = field(default=None, init=False, repr=False)
    _hwnd: int | None = field(default=None, init=False, repr=False)

    def find(self) -> WindowRect:
        try:
            import win32gui
        except ImportError:
            msg = "pywin32 is required: pip install td-executor[win]"
            raise ImportError(msg)

        hwnd = self._find_hwnd(win32gui)
        if hwnd is None:
            msg = f"找不到窗口: title={self.window_title!r}, class={self.window_class!r}"
            raise WindowNotFoundError(msg)

        if win32gui.IsIconic(hwnd):
            msg = f"窗口已最小化: hwnd={hwnd}"
            raise WindowMinimizedError(msg)

        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        if right - left <= 0 or bottom - top <= 0:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        screen_left, screen_top, _, _ = win32gui.ClientToScreen(hwnd, (0, 0))
        width = right - left
        height = bottom - top

        rect = WindowRect(
            left=screen_left,
            top=screen_top,
            width=max(width, 1),
            height=max(height, 1),
        )
        self._hwnd = hwnd
        self._rect = rect
        return rect

    def refresh(self) -> WindowRect:
        self._rect = None
        self._hwnd = None
        return self.find()

    @property
    def rect(self) -> WindowRect:
        if self._rect is None:
            return self.find()
        return self._rect

    @property
    def hwnd(self) -> int:
        if self._hwnd is None:
            self.find()
        return self._hwnd  # type: ignore[return-value]

    def _find_hwnd(self, win32gui: object) -> int | None:
        result: int | None = None

        def _callback(hwnd: int, _ctx: object) -> bool:
            nonlocal result
            if not win32gui.IsWindowVisible(hwnd):  # type: ignore[attr-defined]
                return True
            if self.window_title:
                title = win32gui.GetWindowText(hwnd)  # type: ignore[attr-defined]
                if self.window_title not in title:
                    return True
            if self.window_class:
                cls = win32gui.GetClassName(hwnd)  # type: ignore[attr-defined]
                if self.window_class not in cls:
                    return True
            result = hwnd
            return False

        win32gui.EnumWindows(_callback, None)  # type: ignore[attr-defined]
        return result
