"""已连接窗口截图：ScreenshotManager 与截图后端抽象。"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime

from nzfz_executor.core.models import (
    CaptureBackendType,
    CaptureOptions,
    CaptureRegion,
    ConnectedWindow,
    ScreenshotResult,
    WindowRect,
)

logger = logging.getLogger(__name__)

_OCCLUSION_WARNING = (
    "当前截图后端不支持被遮挡窗口截图，"
    "若窗口被遮挡，截图内容可能不准确"
)

_WGC_UNAVAILABLE_MSG = (
    "Windows Graphics Capture 当前不可用，请检查系统版本或依赖环境"
)

_WGC_FALLBACK_AFTER_FAIL_MSG = (
    "Windows Graphics Capture 截图失败，已回退到屏幕截图；"
    "若窗口被遮挡，截图内容可能不准确"
)

_WGC_FALLBACK_UNAVAILABLE_MSG = (
    "Windows Graphics Capture 当前不可用，已使用屏幕截图；"
    "若窗口被遮挡，截图内容可能不准确"
)


def _is_windows_supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32gui  # noqa: F401
    except ImportError:
        return False
    return True


def _is_window(hwnd: int) -> bool:
    import win32gui

    return bool(win32gui.IsWindow(hwnd))


def _is_window_visible(hwnd: int) -> bool:
    import win32gui

    return bool(win32gui.IsWindowVisible(hwnd))


def _is_window_minimized(hwnd: int) -> bool:
    import win32gui

    return bool(win32gui.IsIconic(hwnd))


def _is_foreground_window(hwnd: int) -> bool:
    import win32gui

    return win32gui.GetForegroundWindow() == hwnd


def _get_window_rect(hwnd: int) -> WindowRect | None:
    import win32gui

    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return WindowRect(left, top, right, bottom)
    except Exception as exc:
        logger.debug("获取窗口矩形失败，hwnd=%s，错误：%s", hwnd, exc)
        return None


def _get_client_rect_on_screen(hwnd: int) -> WindowRect | None:
    import win32gui

    try:
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        s_left, s_top = win32gui.ClientToScreen(hwnd, (c_left, c_top))
        s_right, s_bottom = win32gui.ClientToScreen(
            hwnd,
            (c_right, c_bottom),
        )
        return WindowRect(
            left=s_left,
            top=s_top,
            right=s_right,
            bottom=s_bottom,
        )
    except Exception as exc:
        logger.debug("获取客户区矩形失败，hwnd=%s，错误：%s", hwnd, exc)
        return None


class ScreenshotBackend(ABC):
    """截图后端抽象基类。"""

    backend_type: CaptureBackendType
    supports_occluded: bool = False

    @abstractmethod
    def capture(
        self,
        context: ConnectedWindow,
        options: CaptureOptions,
    ) -> ScreenshotResult:
        """对已连接窗口执行截图。"""


class ScreenCaptureBackend(ScreenshotBackend):
    """基于屏幕区域截取的截图后端。"""

    backend_type = CaptureBackendType.SCREEN
    supports_occluded = False

    def capture(
        self,
        context: ConnectedWindow,
        options: CaptureOptions,
    ) -> ScreenshotResult:
        if not _is_windows_supported():
            return self._failure(
                context=context,
                options=options,
                message="当前平台不支持窗口截图",
            )

        hwnd = context.hwnd
        window_title = context.title

        if not _is_window(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口已失效，请重新连接",
            )

        if not _is_window_visible(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口不可见，无法截图",
            )

        if _is_window_minimized(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口已最小化，无法截图",
            )

        if options.require_foreground and not _is_foreground_window(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口未在前台，无法截图",
            )

        window_rect = _get_window_rect(hwnd)
        client_rect = _get_client_rect_on_screen(hwnd)

        target_rect = (
            client_rect
            if options.region == CaptureRegion.CLIENT
            else window_rect
        )

        if target_rect is None or not target_rect.is_valid():
            return self._failure(
                context=context,
                options=options,
                window_rect=window_rect,
                client_rect=client_rect,
                message="截图区域尺寸无效",
            )

        from PIL import ImageGrab

        image = ImageGrab.grab(
            bbox=(
                target_rect.left,
                target_rect.top,
                target_rect.right,
                target_rect.bottom,
            )
        )

        message = ""
        if options.allow_occluded and not self.supports_occluded:
            message = _OCCLUSION_WARNING

        return ScreenshotResult(
            success=True,
            image=image,
            width=image.width,
            height=image.height,
            captured_at=datetime.now(),
            hwnd=hwnd,
            window_title=window_title,
            region=options.region,
            backend=self.backend_type,
            window_rect=window_rect,
            client_rect=client_rect,
            supports_occluded=self.supports_occluded,
            message=message,
        )

    def _failure(
        self,
        *,
        context: ConnectedWindow,
        options: CaptureOptions,
        message: str,
        window_rect: WindowRect | None = None,
        client_rect: WindowRect | None = None,
    ) -> ScreenshotResult:
        return ScreenshotResult(
            success=False,
            image=None,
            hwnd=context.hwnd,
            window_title=context.title,
            region=options.region,
            backend=self.backend_type,
            window_rect=window_rect,
            client_rect=client_rect,
            supports_occluded=self.supports_occluded,
            message=message,
        )


class WindowsGraphicsCaptureBackend(ScreenshotBackend):
    """基于 Windows Graphics Capture 的窗口内容截图后端。"""

    backend_type = CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
    supports_occluded = True

    def is_available(self) -> bool:
        from nzfz_executor.core.wgc_capture import is_wgc_available

        available = is_wgc_available()
        logger.debug("Windows Graphics Capture available: %s", available)
        return available

    def capture(
        self,
        context: ConnectedWindow,
        options: CaptureOptions,
    ) -> ScreenshotResult:
        if not self.is_available():
            return self._failure(
                context=context,
                options=options,
                message=_WGC_UNAVAILABLE_MSG,
            )

        hwnd = context.hwnd
        window_title = context.title

        if not _is_window(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口已失效，请重新连接",
            )

        if not _is_window_visible(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口不可见，无法截图",
            )

        if _is_window_minimized(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口已最小化，无法截图",
            )

        if options.require_foreground and not _is_foreground_window(hwnd):
            return self._failure(
                context=context,
                options=options,
                message="窗口未在前台，无法截图",
            )

        window_rect = _get_window_rect(hwnd)
        client_rect = _get_client_rect_on_screen(hwnd)

        try:
            from nzfz_executor.core.wgc_capture import (
                capture_hwnd_to_image,
                crop_captured_image,
            )

            image = capture_hwnd_to_image(hwnd)
            image = crop_captured_image(
                image,
                region=options.region,
                window_rect=window_rect or context.window_rect,
                client_rect=client_rect or context.client_rect,
            )
            if image.mode != "RGB":
                image = image.convert("RGB")
        except Exception as exc:
            logger.warning(
                "Windows Graphics Capture failed for hwnd=%s: %s",
                hwnd,
                exc,
            )
            return self._failure(
                context=context,
                options=options,
                window_rect=window_rect,
                client_rect=client_rect,
                message=f"Windows Graphics Capture 截图失败：{exc}",
            )

        return ScreenshotResult(
            success=True,
            image=image,
            width=image.width,
            height=image.height,
            captured_at=datetime.now(),
            hwnd=hwnd,
            window_title=window_title,
            region=options.region,
            backend=self.backend_type,
            window_rect=window_rect,
            client_rect=client_rect,
            supports_occluded=self.supports_occluded,
            message="",
        )

    def _failure(
        self,
        *,
        context: ConnectedWindow,
        options: CaptureOptions,
        message: str,
        window_rect: WindowRect | None = None,
        client_rect: WindowRect | None = None,
    ) -> ScreenshotResult:
        return ScreenshotResult(
            success=False,
            image=None,
            hwnd=context.hwnd,
            window_title=context.title,
            region=options.region,
            backend=self.backend_type,
            window_rect=window_rect,
            client_rect=client_rect,
            supports_occluded=self.supports_occluded,
            message=message,
        )


class ScreenshotManager:
    """已连接窗口截图管理器。"""

    def __init__(self) -> None:
        self._screen_backend = ScreenCaptureBackend()
        self._wgc_backend = WindowsGraphicsCaptureBackend()

    def capture(
        self,
        context: ConnectedWindow | None,
        options: CaptureOptions | None = None,
    ) -> ScreenshotResult:
        options = options or CaptureOptions()

        if context is None:
            return ScreenshotResult(
                success=False,
                region=options.region,
                backend=self._resolve_backend_type(options),
                message="当前未连接游戏窗口",
            )

        if options.backend == CaptureBackendType.AUTO:
            return self._capture_auto(context, options)

        backend = self._select_backend(options)
        if backend is None:
            return ScreenshotResult(
                success=False,
                hwnd=context.hwnd,
                window_title=context.title,
                region=options.region,
                backend=options.backend,
                message="当前截图后端暂未实现",
            )

        return backend.capture(context, options)

    def _capture_auto(
        self,
        context: ConnectedWindow,
        options: CaptureOptions,
    ) -> ScreenshotResult:
        if self._wgc_backend.is_available():
            wgc_result = self._wgc_backend.capture(context, options)
            if wgc_result.success:
                return wgc_result

            logger.warning(
                "Fallback to ScreenCaptureBackend because WGC failed, hwnd=%s",
                context.hwnd,
            )
            screen_result = self._screen_backend.capture(context, options)
            if screen_result.success:
                screen_result.message = _WGC_FALLBACK_AFTER_FAIL_MSG
            return screen_result if screen_result.success else wgc_result

        screen_result = self._screen_backend.capture(context, options)
        if screen_result.success:
            screen_result.message = _WGC_FALLBACK_UNAVAILABLE_MSG
        return screen_result

    def _resolve_backend_type(self, options: CaptureOptions) -> CaptureBackendType:
        if options.backend == CaptureBackendType.AUTO:
            if self._wgc_backend.is_available():
                return CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
            return CaptureBackendType.SCREEN
        return options.backend

    def _select_backend(self, options: CaptureOptions) -> ScreenshotBackend | None:
        if options.backend == CaptureBackendType.SCREEN:
            return self._screen_backend

        if options.backend == CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE:
            return self._wgc_backend

        if options.backend == CaptureBackendType.PRINT_WINDOW:
            return None

        return self._screen_backend
