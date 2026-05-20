"""屏幕截图：定义截图后端枚举、截图配置数据类与截图控制器。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CaptureBackend(Enum):
    """截图后端枚举，标识可用的截图引擎。"""

    MSS = "mss"
    DXCAM = "dxcam"


@dataclass
class CaptureConfig:
    """截图配置数据类，封装后端选择、截取区域与输出格式。"""

    backend: CaptureBackend = CaptureBackend.MSS
    region: dict | None = None
    output_format: str = "bgr"


class ScreenCapture:
    """屏幕截图控制器：管理截图会话的启动与帧捕获。"""

    def __init__(self, config: CaptureConfig | None = None) -> None:
        """初始化截图控制器。

        Args:
            config: 截图配置，为 None 时使用默认配置。
        """
        self.config: CaptureConfig = config or CaptureConfig()

    def start(self) -> None:
        """启动截图会话，初始化后端资源。"""
        raise NotImplementedError

    def close(self) -> None:
        """关闭截图会话，释放后端资源。"""
        raise NotImplementedError

    def capture_frame(self) -> Any:
        """捕获一帧屏幕图像，返回 numpy.ndarray。"""
        raise NotImplementedError