"""P2-01 已连接窗口截图基础能力测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from nzfz_executor.core.models import (
    CaptureBackendType,
    CaptureOptions,
    CaptureRegion,
    ConnectedWindow,
    ScreenshotResult,
    WindowRect,
)
from nzfz_executor.core.screenshot_manager import (
    ScreenCaptureBackend,
    ScreenshotManager,
    WindowsGraphicsCaptureBackend,
)
from nzfz_executor.core.window_manager import WindowManager


def _connected_window(
    *,
    hwnd: int = 100,
    window_rect: WindowRect | None = None,
    client_rect: WindowRect | None = None,
) -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=hwnd,
        title="Game",
        process_name="game.exe",
        pid=1234,
        window_rect=window_rect or WindowRect(0, 0, 800, 600),
        client_rect=client_rect or WindowRect(10, 20, 790, 580),
    )


class TestCaptureModels:
    def test_default_capture_options(self) -> None:
        options = CaptureOptions()
        assert options.region == CaptureRegion.CLIENT
        assert options.backend == CaptureBackendType.AUTO
        assert options.require_foreground is False
        assert options.allow_occluded is True

    def test_screenshot_result_success(self) -> None:
        image = Image.new("RGB", (100, 50))
        result = ScreenshotResult(
            success=True,
            image=image,
            width=100,
            height=50,
            captured_at=datetime.now(),
        )
        assert result.success is True
        assert result.image is not None
        assert result.width == 100
        assert result.height == 50

    def test_screenshot_result_failure(self) -> None:
        result = ScreenshotResult(success=False, message="fail")
        assert result.success is False
        assert result.image is None


class TestWindowManagerContext:
    def test_get_connected_context_when_disconnected(self) -> None:
        wm = WindowManager()
        assert wm.get_connected_context() is None

    def test_get_connected_context_when_connected(self) -> None:
        wm = WindowManager()
        connected = _connected_window()
        wm._connected_window = connected
        assert wm.get_connected_context() is connected
        assert wm.get_connected_window() is connected

    def test_get_connected_context_after_disconnect(self) -> None:
        wm = WindowManager()
        wm._connected_window = _connected_window()
        wm.disconnect_window()
        assert wm.get_connected_context() is None

    def test_get_connected_context_does_not_mutate_state(self) -> None:
        wm = WindowManager()
        wm._connected_window = _connected_window()
        before = wm.get_connected_context()
        after = wm.get_connected_context()
        assert before is after
        assert wm.is_connected() is True


class TestScreenshotManager:
    def test_capture_without_context(self) -> None:
        manager = ScreenshotManager()
        with patch.object(
            WindowsGraphicsCaptureBackend,
            "is_available",
            return_value=False,
        ):
            result = manager.capture(None)
        assert result.success is False
        assert result.message == "当前未连接游戏窗口"
        assert result.backend == CaptureBackendType.SCREEN

    def test_capture_default_options(self) -> None:
        manager = ScreenshotManager()
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "is_available",
                return_value=False,
            ),
            patch.object(ScreenCaptureBackend, "capture") as mock_capture,
        ):
            mock_capture.return_value = ScreenshotResult(success=True)
            context = _connected_window()
            manager.capture(context)
            mock_capture.assert_called_once()
            args = mock_capture.call_args
            assert isinstance(args[0][1], CaptureOptions)

    @pytest.mark.parametrize(
        "backend",
        [
            CaptureBackendType.AUTO,
            CaptureBackendType.SCREEN,
        ],
    )
    def test_select_screen_backend(self, backend: CaptureBackendType) -> None:
        manager = ScreenshotManager()
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "is_available",
                return_value=False,
            ),
            patch.object(ScreenCaptureBackend, "capture") as mock_capture,
        ):
            mock_capture.return_value = ScreenshotResult(success=True)
            manager.capture(
                _connected_window(),
                CaptureOptions(backend=backend),
            )
            mock_capture.assert_called_once()

    def test_unimplemented_print_window_backend(self) -> None:
        manager = ScreenshotManager()
        result = manager.capture(
            _connected_window(),
            CaptureOptions(backend=CaptureBackendType.PRINT_WINDOW),
        )
        assert result.success is False
        assert result.message == "当前截图后端暂未实现"
        assert result.backend == CaptureBackendType.PRINT_WINDOW

    def test_auto_uses_wgc_when_available(self) -> None:
        manager = ScreenshotManager()
        wgc_result = ScreenshotResult(
            success=True,
            backend=CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE,
            supports_occluded=True,
        )
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "is_available",
                return_value=True,
            ),
            patch.object(
                WindowsGraphicsCaptureBackend,
                "capture",
                return_value=wgc_result,
            ) as mock_wgc,
            patch.object(ScreenCaptureBackend, "capture") as mock_screen,
        ):
            result = manager.capture(
                _connected_window(),
                CaptureOptions(backend=CaptureBackendType.AUTO),
            )
            mock_wgc.assert_called_once()
            mock_screen.assert_not_called()
            assert result is wgc_result

    def test_auto_fallback_to_screen_when_wgc_fails(self) -> None:
        manager = ScreenshotManager()
        wgc_result = ScreenshotResult(
            success=False,
            backend=CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE,
            message="WGC fail",
        )
        screen_result = ScreenshotResult(
            success=True,
            backend=CaptureBackendType.SCREEN,
            supports_occluded=False,
        )
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "is_available",
                return_value=True,
            ),
            patch.object(
                WindowsGraphicsCaptureBackend,
                "capture",
                return_value=wgc_result,
            ),
            patch.object(
                ScreenCaptureBackend,
                "capture",
                return_value=screen_result,
            ) as mock_screen,
        ):
            result = manager.capture(
                _connected_window(),
                CaptureOptions(backend=CaptureBackendType.AUTO),
            )
            mock_screen.assert_called_once()
            assert result.success is True
            assert result.backend == CaptureBackendType.SCREEN
            assert "回退" in result.message

    def test_auto_uses_screen_when_wgc_unavailable(self) -> None:
        manager = ScreenshotManager()
        screen_result = ScreenshotResult(
            success=True,
            backend=CaptureBackendType.SCREEN,
            supports_occluded=False,
        )
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "is_available",
                return_value=False,
            ),
            patch.object(
                ScreenCaptureBackend,
                "capture",
                return_value=screen_result,
            ) as mock_screen,
            patch.object(WindowsGraphicsCaptureBackend, "capture") as mock_wgc,
        ):
            result = manager.capture(
                _connected_window(),
                CaptureOptions(backend=CaptureBackendType.AUTO),
            )
            mock_wgc.assert_not_called()
            mock_screen.assert_called_once()
            assert result.success is True
            assert "不可用" in result.message

    def test_explicit_wgc_does_not_fallback(self) -> None:
        manager = ScreenshotManager()
        wgc_result = ScreenshotResult(
            success=False,
            backend=CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE,
            message="explicit fail",
        )
        with (
            patch.object(
                WindowsGraphicsCaptureBackend,
                "capture",
                return_value=wgc_result,
            ) as mock_wgc,
            patch.object(ScreenCaptureBackend, "capture") as mock_screen,
        ):
            result = manager.capture(
                _connected_window(),
                CaptureOptions(
                    backend=CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE,
                ),
            )
            mock_wgc.assert_called_once()
            mock_screen.assert_not_called()
            assert result is wgc_result

    def test_explicit_screen_does_not_try_wgc(self) -> None:
        manager = ScreenshotManager()
        with (
            patch.object(ScreenCaptureBackend, "capture") as mock_screen,
            patch.object(WindowsGraphicsCaptureBackend, "capture") as mock_wgc,
        ):
            mock_screen.return_value = ScreenshotResult(success=True)
            manager.capture(
                _connected_window(),
                CaptureOptions(backend=CaptureBackendType.SCREEN),
            )
            mock_screen.assert_called_once()
            mock_wgc.assert_not_called()


class TestScreenCaptureBackend:
    def _run_capture(
        self,
        options: CaptureOptions | None = None,
        *,
        is_window: bool = True,
        is_visible: bool = True,
        is_minimized: bool = False,
        is_foreground: bool = True,
        window_rect: WindowRect | None = None,
        client_rect: WindowRect | None = None,
        grab_size: tuple[int, int] = (780, 560),
    ) -> ScreenshotResult:
        backend = ScreenCaptureBackend()
        context = _connected_window(
            window_rect=window_rect or WindowRect(0, 0, 800, 600),
            client_rect=client_rect or WindowRect(10, 20, 790, 580),
        )
        image = Image.new("RGB", grab_size)

        with (
            patch(
                "nzfz_executor.core.screenshot_manager._is_windows_supported",
                return_value=True,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window",
                return_value=is_window,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window_visible",
                return_value=is_visible,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window_minimized",
                return_value=is_minimized,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_foreground_window",
                return_value=is_foreground,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._get_window_rect",
                return_value=window_rect or WindowRect(0, 0, 800, 600),
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._get_client_rect_on_screen",
                return_value=client_rect or WindowRect(10, 20, 790, 580),
            ),
            patch("PIL.ImageGrab.grab", return_value=image),
        ):
            return backend.capture(context, options or CaptureOptions())

    def test_client_region_success(self) -> None:
        result = self._run_capture(CaptureOptions(region=CaptureRegion.CLIENT))
        assert result.success is True
        assert result.image is not None
        assert result.width == 780
        assert result.height == 560
        assert result.region == CaptureRegion.CLIENT
        assert result.backend == CaptureBackendType.SCREEN

    def test_window_region_success(self) -> None:
        result = self._run_capture(
            CaptureOptions(region=CaptureRegion.WINDOW),
            grab_size=(800, 600),
        )
        assert result.success is True
        assert result.width == 800
        assert result.height == 600
        assert result.region == CaptureRegion.WINDOW

    def test_invalid_hwnd(self) -> None:
        result = self._run_capture(is_window=False)
        assert result.success is False
        assert result.message == "窗口已失效，请重新连接"

    def test_invisible_window(self) -> None:
        result = self._run_capture(is_visible=False)
        assert result.success is False
        assert result.message == "窗口不可见，无法截图"

    def test_minimized_window(self) -> None:
        result = self._run_capture(is_minimized=True)
        assert result.success is False
        assert result.message == "窗口已最小化，无法截图"

    def test_require_foreground_not_foreground(self) -> None:
        result = self._run_capture(
            CaptureOptions(require_foreground=True),
            is_foreground=False,
        )
        assert result.success is False
        assert result.message == "窗口未在前台，无法截图"

    def test_require_foreground_false_allows_background(self) -> None:
        result = self._run_capture(
            CaptureOptions(require_foreground=False),
            is_foreground=False,
        )
        assert result.success is True

    def test_invalid_region_size(self) -> None:
        result = self._run_capture(
            client_rect=WindowRect(10, 20, 10, 20),
            grab_size=(0, 0),
        )
        assert result.success is False
        assert result.message == "截图区域尺寸无效"

    def test_allow_occluded_warning(self) -> None:
        result = self._run_capture(CaptureOptions(allow_occluded=True))
        assert result.success is True
        assert result.supports_occluded is False
        assert "被遮挡" in result.message

    def test_non_windows_platform(self) -> None:
        backend = ScreenCaptureBackend()
        with patch(
            "nzfz_executor.core.screenshot_manager._is_windows_supported",
            return_value=False,
        ):
            result = backend.capture(_connected_window(), CaptureOptions())
        assert result.success is False
        assert result.message == "当前平台不支持窗口截图"


class TestWindowsGraphicsCaptureBackend:
    def _run_capture(
        self,
        options: CaptureOptions | None = None,
        *,
        is_available: bool = True,
        is_window: bool = True,
        is_visible: bool = True,
        is_minimized: bool = False,
        capture_raises: Exception | None = None,
        image_size: tuple[int, int] = (800, 600),
    ) -> ScreenshotResult:
        backend = WindowsGraphicsCaptureBackend()
        context = _connected_window()
        image = Image.new("RGBA", image_size)

        patches = [
            patch.object(backend, "is_available", return_value=is_available),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window",
                return_value=is_window,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window_visible",
                return_value=is_visible,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._is_window_minimized",
                return_value=is_minimized,
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._get_window_rect",
                return_value=WindowRect(0, 0, 800, 600),
            ),
            patch(
                "nzfz_executor.core.screenshot_manager._get_client_rect_on_screen",
                return_value=WindowRect(10, 20, 790, 580),
            ),
        ]

        if capture_raises is not None:
            capture_patch = patch(
                "nzfz_executor.core.wgc_capture.capture_hwnd_to_image",
                side_effect=capture_raises,
            )
        else:
            capture_patch = patch(
                "nzfz_executor.core.wgc_capture.capture_hwnd_to_image",
                return_value=image,
            )

        with capture_patch:
            for item in patches:
                item.start()
            try:
                return backend.capture(context, options or CaptureOptions())
            finally:
                for item in reversed(patches):
                    item.stop()

    def test_unavailable(self) -> None:
        result = self._run_capture(is_available=False)
        assert result.success is False
        assert "不可用" in result.message
        assert result.backend == CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
        assert result.supports_occluded is True

    def test_success(self) -> None:
        result = self._run_capture()
        assert result.success is True
        assert result.backend == CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
        assert result.supports_occluded is True
        assert result.image is not None

    def test_minimized(self) -> None:
        result = self._run_capture(is_minimized=True)
        assert result.success is False
        assert result.message == "窗口已最小化，无法截图"

    def test_capture_exception(self) -> None:
        result = self._run_capture(capture_raises=RuntimeError("gpu error"))
        assert result.success is False
        assert "gpu error" in result.message


class TestWgcCaptureHelpers:
    def test_crop_client_region(self) -> None:
        from nzfz_executor.core.wgc_capture import crop_captured_image

        image = Image.new("RGBA", (800, 600))
        cropped = crop_captured_image(
            image,
            region=CaptureRegion.CLIENT,
            window_rect=WindowRect(0, 0, 800, 600),
            client_rect=WindowRect(10, 20, 790, 580),
        )
        assert cropped.size == (780, 560)

    def test_is_wgc_available_false_on_non_windows(self) -> None:
        from nzfz_executor.core.wgc_capture import is_wgc_available

        with patch("sys.platform", "linux"):
            assert is_wgc_available() is False
