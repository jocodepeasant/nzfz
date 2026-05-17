"""屏幕采集模块：支持 mss / dxcam 后端截取游戏窗口画面。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class CaptureBackend(Enum):
    MSS = "mss"
    DXCAM = "dxcam"


@dataclass
class CaptureConfig:
    backend: CaptureBackend = CaptureBackend.MSS
    region: dict[str, int] | None = None
    output_format: str = "bgr"


class ScreenCapture:
    def __init__(
        self,
        config: CaptureConfig | None = None,
        *,
        backend: CaptureBackend | str = "mss",
        region: dict[str, int] | None = None,
        output_format: str = "bgr",
    ) -> None:
        if config is not None:
            self._config = config
        else:
            be = CaptureBackend(backend) if isinstance(backend, str) else backend
            self._config = CaptureConfig(backend=be, region=region, output_format=output_format)
        self._backend_impl: Any = None
        self._closed = False

    @property
    def config(self) -> CaptureConfig:
        return self._config

    @property
    def closed(self) -> bool:
        return self._closed

    def start(self) -> None:
        if self._closed:
            raise RuntimeError("ScreenCapture 已关闭，无法重新启动")
        if self._backend_impl is not None:
            return
        if self._config.backend == CaptureBackend.MSS:
            self._init_mss()
        elif self._config.backend == CaptureBackend.DXCAM:
            self._init_dxcam()
        else:
            raise ValueError(f"不支持的后端: {self._config.backend}")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._backend_impl is not None:
            if self._config.backend == CaptureBackend.MSS:
                self._backend_impl.close()
            elif self._config.backend == CaptureBackend.DXCAM:
                try:
                    self._backend_impl.release()
                except Exception:
                    pass
            self._backend_impl = None

    def capture_frame(self) -> np.ndarray:
        if self._closed:
            raise RuntimeError("ScreenCapture 已关闭，不能截图")
        if self._backend_impl is None:
            self.start()
        if self._config.backend == CaptureBackend.MSS:
            return self._capture_mss()
        if self._config.backend == CaptureBackend.DXCAM:
            return self._capture_dxcam()
        raise ValueError(f"不支持的后端: {self._config.backend}")

    def __enter__(self) -> ScreenCapture:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _init_mss(self) -> None:
        try:
            import mss
        except ImportError as exc:
            raise ImportError(
                "mss 未安装，请执行: pip install mss"
            ) from exc
        self._backend_impl = mss.mss()

    def _init_dxcam(self) -> None:
        try:
            import dxcam
        except ImportError as exc:
            raise ImportError(
                "dxcam 未安装，请执行: pip install dxcam"
            ) from exc
        self._backend_impl = dxcam.create(output_color="BGR")

    def _capture_mss(self) -> np.ndarray:
        mss_inst = self._backend_impl
        if self._config.region is not None:
            monitor = self._config.region
        else:
            monitor = mss_inst.monitors[0]
        shot = mss_inst.grab(monitor)
        img = np.array(shot, dtype=np.uint8)
        if shot.mode == "RGBA":
            img = img[:, :, :3]
        if self._config.output_format == "bgr":
            pass
        elif self._config.output_format == "rgb":
            img = img[:, :, ::-1]
        else:
            raise ValueError(f"不支持的输出格式: {self._config.output_format}")
        return np.ascontiguousarray(img)

    def _capture_dxcam(self) -> np.ndarray:
        cam = self._backend_impl
        region = self._config.region
        if region is not None:
            left = region.get("left", 0)
            top = region.get("top", 0)
            right = left + region.get("width", 1920)
            bottom = top + region.get("height", 1080)
            img = cam.grab(region=(left, top, right, bottom))
        else:
            img = cam.grab()
        if img is None:
            raise RuntimeError("dxcam 截图返回 None")
        if self._config.output_format == "rgb":
            img = img[:, :, ::-1]
        return np.ascontiguousarray(img)
