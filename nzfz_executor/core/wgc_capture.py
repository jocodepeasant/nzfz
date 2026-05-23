"""Windows Graphics Capture 底层单帧捕获。"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

from nzfz_executor.core.models import CaptureRegion, WindowRect

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

CAPTURE_TIMEOUT_SEC = 5.0


def is_wgc_platform_supported() -> bool:
    """检查当前平台是否满足 WGC 最低系统要求。"""
    if sys.platform != "win32":
        return False
    return sys.getwindowsversion().build >= 18362


def _get_direct3d_device():
    from winsdk.windows.ai.machinelearning import (
        LearningModelDevice,
        LearningModelDeviceKind,
    )

    try:
        device = LearningModelDevice(
            LearningModelDeviceKind.DIRECT_X_HIGH_PERFORMANCE,
        ).direct3_d11_device
        if device is not None:
            return device
    except Exception as exc:
        logger.debug("DirectX high performance device unavailable: %s", exc)

    from winsdk.windows.media.capture import MediaCapture

    media_capture = MediaCapture()

    async def _initialize() -> None:
        await media_capture.initialize_async()

    asyncio.run(_initialize())
    settings = media_capture.media_capture_settings
    if settings is None or settings.direct3_d11_device is None:
        raise OSError("Unable to initialize a Direct3D Device.")
    return settings.direct3_d11_device


def is_wgc_available() -> bool:
    """检查 WGC 依赖与 Direct3D 是否可用。"""
    if not is_wgc_platform_supported():
        return False
    try:
        from winsdk.windows.graphics.capture.interop import (  # noqa: F401
            create_for_window,
        )

        _get_direct3d_device()
        return True
    except Exception as exc:
        logger.debug("Windows Graphics Capture available: False (%s)", exc)
        return False


async def _capture_frame_async(hwnd: int, timeout_sec: float) -> Image.Image:
    from winsdk.windows.graphics.capture import Direct3D11CaptureFramePool
    from winsdk.windows.graphics.capture.interop import create_for_window
    from winsdk.windows.graphics.directx import DirectXPixelFormat
    from winsdk.windows.graphics.imaging import (
        BitmapBufferAccessMode,
        SoftwareBitmap,
    )

    device = _get_direct3d_device()
    item = create_for_window(hwnd)
    size = item.size

    frame_pool = Direct3D11CaptureFramePool.create_free_threaded(
        device,
        DirectXPixelFormat.B8_G8_R8_A8_UINT_NORMALIZED,
        1,
        size,
    )
    session = frame_pool.create_capture_session(item)
    session.is_border_required = False
    session.is_cursor_capture_enabled = False

    loop = asyncio.get_running_loop()
    frame_future: asyncio.Future = loop.create_future()

    def _on_frame_arrived(frame_pool_obj, _event_args) -> None:
        if frame_future.done():
            return
        frame = frame_pool_obj.try_get_next_frame()
        if frame is None:
            return
        loop.call_soon_threadsafe(frame_future.set_result, frame)
        session.close()

    frame_pool.add_frame_arrived(_on_frame_arrived)
    session.start_capture()

    try:
        capture_frame = await asyncio.wait_for(frame_future, timeout=timeout_sec)
        software_bitmap = await SoftwareBitmap.create_copy_from_surface_async(
            capture_frame.surface,
        )
        buffer = software_bitmap.lock_buffer(BitmapBufferAccessMode.READ)
        try:
            pixel_bytes = bytes(buffer.create_reference())
        finally:
            buffer.close()

        from PIL import Image

        return Image.frombytes(
            "RGBA",
            (size.width, size.height),
            pixel_bytes,
        )
    finally:
        try:
            session.close()
        except Exception:
            pass
        try:
            frame_pool.close()
        except Exception:
            pass


def crop_captured_image(
    image: Image.Image,
    *,
    region: CaptureRegion,
    window_rect: WindowRect,
    client_rect: WindowRect,
) -> Image.Image:
    """按 CaptureRegion 裁剪 WGC 整窗图像，考虑 DPI 缩放。"""
    if region == CaptureRegion.WINDOW:
        return image

    win_w = window_rect.width
    win_h = window_rect.height
    if win_w <= 0 or win_h <= 0:
        return image

    scale_x = image.width / win_w
    scale_y = image.height / win_h
    left = int((client_rect.left - window_rect.left) * scale_x)
    top = int((client_rect.top - window_rect.top) * scale_y)
    right = int(left + client_rect.width * scale_x)
    bottom = int(top + client_rect.height * scale_y)
    return image.crop((left, top, right, bottom))


def capture_hwnd_to_image(
    hwnd: int,
    *,
    timeout_sec: float = CAPTURE_TIMEOUT_SEC,
) -> Image.Image:
    """从窗口句柄捕获一帧并返回 RGBA PIL Image。"""
    return asyncio.run(_capture_frame_async(hwnd, timeout_sec))
