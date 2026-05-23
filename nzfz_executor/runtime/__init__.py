"""运行时能力模块：提供窗口管理、屏幕截图、输入模拟与叠加层渲染。"""

from nzfz_executor.runtime.capture import CaptureBackend, CaptureConfig, ScreenCapture
from nzfz_executor.runtime.input import InputController
from nzfz_executor.runtime.overlay import OverlayRenderer
from nzfz_executor.runtime.window import WindowInfo, WindowManager, from_connected_window

__all__ = [
    "WindowInfo",
    "WindowManager",
    "from_connected_window",
    "ScreenCapture",
    "CaptureBackend",
    "CaptureConfig",
    "InputController",
    "OverlayRenderer",
]