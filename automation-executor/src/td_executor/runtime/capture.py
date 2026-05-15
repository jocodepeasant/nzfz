"""屏幕采集抽象层。"""

from abc import ABC, abstractmethod


def roi_to_pixel_bounds(
    window_rect: tuple[int, int, int, int],
    x_ratio: float,
    y_ratio: float,
    w_ratio: float,
    h_ratio: float,
) -> tuple[int, int, int, int]:
    left, top, width, height = window_rect
    px = int(left + width * x_ratio)
    py = int(top + height * y_ratio)
    pw = int(width * w_ratio)
    ph = int(height * h_ratio)
    return px, py, pw, ph


class ScreenCapture(ABC):
    def __init__(self, window_rect: tuple[int, int, int, int]) -> None:
        self.window_rect = window_rect

    @abstractmethod
    def capture_full(self) -> "numpy.ndarray":
        ...

    @abstractmethod
    def capture_roi(
        self,
        x_ratio: float,
        y_ratio: float,
        w_ratio: float,
        h_ratio: float,
    ) -> "numpy.ndarray":
        ...


class MssCapture(ScreenCapture):
    def capture_full(self) -> "numpy.ndarray":
        import numpy
        import mss

        left, top, width, height = self.window_rect
        monitor = {"left": left, "top": top, "width": width, "height": height}
        with mss.mss() as sct:
            shot = sct.grab(monitor)
        return numpy.array(shot, dtype=numpy.uint8)[:, :, :3]

    def capture_roi(
        self,
        x_ratio: float,
        y_ratio: float,
        w_ratio: float,
        h_ratio: float,
    ) -> "numpy.ndarray":
        import numpy
        import mss

        px, py, pw, ph = roi_to_pixel_bounds(
            self.window_rect, x_ratio, y_ratio, w_ratio, h_ratio
        )
        monitor = {"left": px, "top": py, "width": pw, "height": ph}
        with mss.mss() as sct:
            shot = sct.grab(monitor)
        return numpy.array(shot, dtype=numpy.uint8)[:, :, :3]


class DxcamCapture(ScreenCapture):
    def __init__(self, window_rect: tuple[int, int, int, int]) -> None:
        super().__init__(window_rect)
        import dxcam

        self._camera = dxcam.create(output_idx=0)

    def capture_full(self) -> "numpy.ndarray":
        import numpy

        left, top, width, height = self.window_rect
        frame = self._camera.grab(region=(left, top, left + width, top + height))
        if frame is None:
            raise RuntimeError("dxcam 截图失败")
        return numpy.ascontiguousarray(frame[:, :, :3])

    def capture_roi(
        self,
        x_ratio: float,
        y_ratio: float,
        w_ratio: float,
        h_ratio: float,
    ) -> "numpy.ndarray":
        import numpy

        left, top, width, height = self.window_rect
        frame = self._camera.grab(region=(left, top, left + width, top + height))
        if frame is None:
            raise RuntimeError("dxcam 截图失败")
        px, py, pw, ph = roi_to_pixel_bounds(
            self.window_rect, x_ratio, y_ratio, w_ratio, h_ratio
        )
        rx = px - left
        ry = py - top
        return numpy.ascontiguousarray(frame[ry : ry + ph, rx : rx + pw, :3])


def create_capture(
    backend: str = "mss",
    window_rect: tuple[int, int, int, int] = (0, 0, 1920, 1080),
) -> ScreenCapture:
    if backend == "mss":
        return MssCapture(window_rect)
    if backend == "dxcam":
        return DxcamCapture(window_rect)
    raise ValueError(f"不支持的截图后端: {backend}")
