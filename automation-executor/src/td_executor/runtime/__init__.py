"""窗口、坐标、截图运行时能力。"""

from td_executor.runtime.capture import CaptureBackend, CaptureConfig, ScreenCapture
from td_executor.runtime.coordinates import ratio_to_pixel

__all__ = [
    "CaptureBackend",
    "CaptureConfig",
    "ScreenCapture",
    "ratio_to_pixel",
]
