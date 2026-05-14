from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from td_executor.runtime.window import WindowRect


class CaptureError(Exception):
    pass


def capture_frame(rect: WindowRect) -> np.ndarray:
    import numpy as np

    img = _mss_capture(rect)
    if img is not None:
        return img

    try:
        img = _mss_capture(rect)
        if img is not None:
            return img
    except Exception:
        pass

    msg = f"截图失败: rect=({rect.left}, {rect.top}, {rect.width}, {rect.height})"
    raise CaptureError(msg)


def capture_roi(rect: WindowRect, roi: dict[str, float]) -> np.ndarray:
    import numpy as np

    from td_executor.runtime.coordinates import ratio_rect_to_pixel

    x, y, w, h = ratio_rect_to_pixel(
        rect.left, rect.top, rect.width, rect.height,
        roi["x_ratio"], roi["y_ratio"], roi["w_ratio"], roi["h_ratio"],
    )
    full = capture_frame(rect)
    x_local = x - rect.left
    y_local = y - rect.top
    x_local = max(0, min(x_local, full.shape[1] - 1))
    y_local = max(0, min(y_local, full.shape[0] - 1))
    h = min(h, full.shape[0] - y_local)
    w = min(w, full.shape[1] - x_local)
    return full[y_local:y_local + h, x_local:x_local + w].copy()


def _mss_capture(rect: WindowRect) -> np.ndarray | None:
    try:
        import numpy as np
        import mss
    except ImportError:
        msg = "mss and numpy are required: pip install td-executor[runtime]"
        raise ImportError(msg)

    monitor = {
        "left": rect.left,
        "top": rect.top,
        "width": rect.width,
        "height": rect.height,
    }
    try:
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            img = np.array(shot, dtype=np.uint8)
            return img[:, :, :3].copy()
    except Exception:
        return None
