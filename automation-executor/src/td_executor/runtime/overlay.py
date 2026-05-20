from __future__ import annotations

import sys
import logging
from ctypes import wintypes

logger = logging.getLogger(__name__)

WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8
WS_EX_TOOLWINDOW = 0x80
WS_POPUP = 0x80000000
WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_DESTROY = 0x0002
LWA_COLORKEY = 0x1
SWP_NOMOVE = 0x2
SWP_NOSIZE = 0x1
SWP_NOACTIVATE = 0x10
COLOR_KEY = 1 | (1 << 8) | (1 << 16)

if sys.platform == "win32":
    import ctypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    user32.CreateWindowExW.restype = ctypes.c_void_p
    user32.BeginPaint.restype = ctypes.c_void_p
    gdi32.CreateSolidBrush.restype = ctypes.c_void_p
    gdi32.CreatePen.restype = ctypes.c_void_p
    gdi32.SelectObject.restype = ctypes.c_void_p
    gdi32.GetStockObject.restype = ctypes.c_void_p
    gdi32.CreateFontW.restype = ctypes.c_void_p

    WNDPROC = ctypes.WINFUNCTYPE(
        wintypes.LPARAM, wintypes.HWND, wintypes.UINT,
        wintypes.WPARAM, wintypes.LPARAM,
    )

    _overlay_instances: dict = {}

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG), ("top", wintypes.LONG),
            ("right", wintypes.LONG), ("bottom", wintypes.LONG),
        ]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class _PAINTSTRUCT(ctypes.Structure):
        _fields_ = [
            ("hdc", wintypes.HDC),
            ("fErase", wintypes.BOOL),
            ("rcPaint", _RECT),
            ("fRestore", wintypes.BOOL),
            ("fIncUpdate", wintypes.BOOL),
            ("rgbReserved", ctypes.c_byte * 32),
        ]

    class _WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HICON),
        ]

    _wndproc_ref = None
    _class_registered = False

    def _ensure_class_registered() -> bool:
        global _wndproc_ref, _class_registered
        if _class_registered:
            return True

        @WNDPROC
        def _overlay_wnd_proc(hwnd, msg, wparam, lparam):
            overlay = _overlay_instances.get(hwnd)
            if msg == WM_PAINT:
                if overlay is not None:
                    overlay._redraw(
                        include_click=overlay._click_marker is not None,
                        click_x=overlay._click_marker[0] if overlay._click_marker else 0,
                        click_y=overlay._click_marker[1] if overlay._click_marker else 0,
                        include_key=overlay._key_text is not None,
                        key_text=overlay._key_text or "",
                    )
                else:
                    ps = _PAINTSTRUCT()
                    user32.BeginPaint(hwnd, ctypes.byref(ps))
                    user32.EndPaint(hwnd, ctypes.byref(ps))
                return 0
            elif msg == WM_TIMER:
                if overlay is not None:
                    timer_id = wparam
                    if timer_id == 9999:
                        if overlay._hwnd_overlay:
                            overlay._sync_position()
                        return 0
                    user32.KillTimer(hwnd, timer_id)
                    if timer_id in overlay._timer_ids:
                        overlay._timer_ids.remove(timer_id)
                    action = overlay._timer_actions.pop(timer_id, None)
                    if action == "click":
                        overlay._click_marker = None
                    elif action == "key":
                        overlay._key_text = None
                    user32.InvalidateRect(hwnd, None, True)
                return 0
            elif msg == WM_DESTROY:
                if overlay is not None:
                    for tid in list(overlay._timer_ids):
                        user32.KillTimer(hwnd, tid)
                    overlay._timer_ids.clear()
                    overlay._timer_actions.clear()
                    overlay._hwnd_overlay = 0
                    overlay._click_marker = None
                    overlay._key_text = None
                    _overlay_instances.pop(hwnd, None)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        _wndproc_ref = _overlay_wnd_proc

        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = _wndproc_ref
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.hIcon = 0
        wc.hCursor = 0
        wc.hbrBackground = gdi32.CreateSolidBrush(COLOR_KEY)
        wc.lpszMenuName = None
        wc.lpszClassName = "TDOverlayClass"
        wc.hIconSm = 0

        if not user32.RegisterClassExW(ctypes.byref(wc)):
            logger.error("RegisterClassExW 失败: %d", kernel32.GetLastError())
            return False

        _class_registered = True
        return True

    class WindowOverlay:
        def __init__(self) -> None:
            self._hwnd_overlay: int = 0
            self._hwnd_target: int = 0
            self._timer_ids: list[int] = []
            self._timer_actions: dict[int, str] = {}
            self._click_marker: tuple[int, int] | None = None
            self._key_text: str | None = None
            self._next_timer_id: int = 1
            self._last_rect: tuple[int, int, int, int] | None = None
            self._debug_info: str = ""
            self._log_lines: list[str] = []

        def show(self, hwnd: int, window_info: str = "") -> bool:
            if self._hwnd_overlay:
                self.hide()
            if not _ensure_class_registered():
                return False
            self._hwnd_target = hwnd
            rect = _RECT()
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                logger.error("GetClientRect 失败")
                return False
            pt = _POINT(rect.left, rect.top)
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            x = pt.x
            y = pt.y
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
            style = WS_POPUP
            hwnd_overlay = user32.CreateWindowExW(
                ex_style, "TDOverlayClass", "TDOverlay",
                style, x, y, w, h,
                0, 0, kernel32.GetModuleHandleW(None), 0,
            )
            if not hwnd_overlay:
                logger.error("CreateWindowExW 失败: %d", kernel32.GetLastError())
                return False
            self._hwnd_overlay = hwnd_overlay
            _overlay_instances[hwnd_overlay] = self
            self._debug_info = window_info
            self._log_lines = []
            self._last_rect = (x, y, w, h)
            user32.SetLayeredWindowAttributes(hwnd_overlay, COLOR_KEY, 0, LWA_COLORKEY)
            user32.SetWindowPos(
                hwnd_overlay, -1,
                x, y, w, h,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
            user32.ShowWindow(hwnd_overlay, 4)
            self._start_sync_timer()
            return True

        def _start_sync_timer(self) -> None:
            if self._hwnd_overlay and sys.platform == "win32":
                user32.SetTimer(self._hwnd_overlay, 9999, 500, None)
                self._timer_ids.append(9999)
                self._timer_actions[9999] = "sync"

        def _sync_position(self) -> None:
            if not self._hwnd_target or not self._hwnd_overlay:
                return
            if not user32.IsWindow(self._hwnd_target):
                self.hide()
                return
            rect = _RECT()
            if not user32.GetClientRect(self._hwnd_target, ctypes.byref(rect)):
                self.hide()
                return
            pt = _POINT(rect.left, rect.top)
            user32.ClientToScreen(self._hwnd_target, ctypes.byref(pt))
            x, y = pt.x, pt.y
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if self._last_rect != (x, y, w, h):
                self._last_rect = (x, y, w, h)
                user32.SetWindowPos(self._hwnd_overlay, -1, x, y, w, h, 0x0040 | 0x0001 | 0x0002 | 0x0010)

        def log_operation(self, msg: str) -> None:
            if not self._hwnd_overlay:
                return
            self._log_lines.append(msg)
            if len(self._log_lines) > 20:
                self._log_lines.pop(0)
            user32.InvalidateRect(self._hwnd_overlay, None, True)

        def hide(self) -> bool:
            if not self._hwnd_overlay:
                return True
            for tid in list(self._timer_ids):
                user32.KillTimer(self._hwnd_overlay, tid)
            self._timer_ids.clear()
            self._timer_actions.clear()
            _overlay_instances.pop(self._hwnd_overlay, None)
            result = user32.DestroyWindow(self._hwnd_overlay)
            self._hwnd_overlay = 0
            self._hwnd_target = 0
            self._click_marker = None
            self._key_text = None
            self._last_rect = None
            self._debug_info = ""
            self._log_lines = []
            return bool(result)

        def draw_click_marker(self, x: int, y: int, duration_ms: int = 1500) -> None:
            if not self._hwnd_overlay:
                return
            for tid in list(self._timer_ids):
                if self._timer_actions.get(tid) == "click":
                    user32.KillTimer(self._hwnd_overlay, tid)
                    self._timer_ids.remove(tid)
                    self._timer_actions.pop(tid, None)
            self._click_marker = (x, y)
            timer_id = self._next_timer_id
            self._next_timer_id += 1
            user32.SetTimer(self._hwnd_overlay, timer_id, duration_ms, None)
            self._timer_ids.append(timer_id)
            self._timer_actions[timer_id] = "click"
            user32.InvalidateRect(self._hwnd_overlay, None, True)

        def draw_key_info(self, key: str, hold_ms: int = 0, duration_ms: int = 2000) -> None:
            if not self._hwnd_overlay:
                return
            for tid in list(self._timer_ids):
                if self._timer_actions.get(tid) == "key":
                    user32.KillTimer(self._hwnd_overlay, tid)
                    self._timer_ids.remove(tid)
                    self._timer_actions.pop(tid, None)
            if hold_ms > 0:
                self._key_text = f"按住 {key} {hold_ms}ms"
            else:
                self._key_text = f"按键 {key}"
            timer_id = self._next_timer_id
            self._next_timer_id += 1
            user32.SetTimer(self._hwnd_overlay, timer_id, duration_ms, None)
            self._timer_ids.append(timer_id)
            self._timer_actions[timer_id] = "key"
            user32.InvalidateRect(self._hwnd_overlay, None, True)

        def _redraw(self, include_click=False, click_x=0, click_y=0, include_key=False, key_text="") -> None:
            if not self._hwnd_overlay:
                return
            ps = _PAINTSTRUCT()
            hdc = user32.BeginPaint(self._hwnd_overlay, ctypes.byref(ps))
            if not hdc:
                return
            rect = _RECT()
            user32.GetClientRect(self._hwnd_overlay, ctypes.byref(rect))
            bg_brush = gdi32.CreateSolidBrush(COLOR_KEY)
            gdi32.FillRect(hdc, ctypes.byref(rect), bg_brush)
            gdi32.DeleteObject(bg_brush)
            border_pen = gdi32.CreatePen(0, 3, 0x0000FF)
            old_pen = gdi32.SelectObject(hdc, border_pen)
            null_brush = gdi32.GetStockObject(5)
            old_brush = gdi32.SelectObject(hdc, null_brush)
            gdi32.Rectangle(hdc, 1, 1, rect.right - 1, rect.bottom - 1)
            gdi32.SelectObject(hdc, old_pen)
            gdi32.SelectObject(hdc, old_brush)
            gdi32.DeleteObject(border_pen)
            if self._debug_info:
                font = gdi32.CreateFontW(-14, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 0, 0, "Microsoft YaHei")
                old_font = gdi32.SelectObject(hdc, font)
                gdi32.SetBkMode(hdc, 1)
                buf = ctypes.create_unicode_buffer(self._debug_info)
                text_len = len(self._debug_info)
                gdi32.SetTextColor(hdc, 0x00FFFF)
                gdi32.TextOutW(hdc, 4, 4, buf, text_len)
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(font)
            if self._log_lines:
                font = gdi32.CreateFontW(-12, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Consolas")
                old_font = gdi32.SelectObject(hdc, font)
                gdi32.SetBkMode(hdc, 1)
                bg_brush_log = gdi32.CreateSolidBrush(0)
                gdi32.FillRect(hdc, ctypes.byref(_RECT(0, rect.bottom - min(len(self._log_lines)*16, rect.bottom//2), rect.right, rect.bottom)), bg_brush_log)
                gdi32.DeleteObject(bg_brush_log)
                y_offset = rect.bottom - 16
                for line in reversed(self._log_lines):
                    line_buf = ctypes.create_unicode_buffer(line[:80])
                    line_len = len(line_buf) - 1
                    gdi32.SetTextColor(hdc, 0x00FF00)
                    gdi32.TextOutW(hdc, 4, y_offset - 16, line_buf, line_len)
                    y_offset -= 16
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(font)
            if include_click:
                click_pen = gdi32.CreatePen(0, 2, 0x0000FF)
                old_click_pen = gdi32.SelectObject(hdc, click_pen)
                gdi32.MoveToEx(hdc, click_x - 10, click_y, None)
                gdi32.LineTo(hdc, click_x + 10, click_y)
                gdi32.MoveToEx(hdc, click_x, click_y - 10, None)
                gdi32.LineTo(hdc, click_x, click_y + 10)
                gdi32.SelectObject(hdc, old_click_pen)
                gdi32.DeleteObject(click_pen)
            if include_key and key_text:
                font = gdi32.CreateFontW(
                    -18, 0, 0, 0, 700, 0, 0, 0,
                    1, 0, 0, 0, 0, "Microsoft YaHei",
                )
                old_font = gdi32.SelectObject(hdc, font)
                gdi32.SetBkMode(hdc, 1)
                buf = ctypes.create_unicode_buffer(key_text)
                text_len = len(key_text)
                gdi32.SetTextColor(hdc, 0x000000)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        gdi32.TextOutW(hdc, 10 + dx, 10 + dy, buf, text_len)
                gdi32.SetTextColor(hdc, 0xFFFFFF)
                gdi32.TextOutW(hdc, 10, 10, buf, text_len)
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(font)
            user32.EndPaint(self._hwnd_overlay, ctypes.byref(ps))

else:

    class WindowOverlay:
        def __init__(self) -> None:
            self._hwnd_overlay: int = 0
            self._hwnd_target: int = 0
            self._timer_ids: list[int] = []
            self._last_rect: tuple[int, int, int, int] | None = None
            self._debug_info: str = ""
            self._log_lines: list[str] = []

        def show(self, hwnd: int, window_info: str = "") -> bool:
            return True

        def hide(self) -> bool:
            return True

        def log_operation(self, msg: str) -> None:
            pass

        def draw_click_marker(self, x: int, y: int, duration_ms: int = 1500) -> None:
            pass

        def draw_key_info(self, key: str, hold_ms: int = 0, duration_ms: int = 2000) -> None:
            pass

        def _redraw(self, include_click=False, click_x=0, click_y=0, include_key=False, key_text="") -> None:
            pass
