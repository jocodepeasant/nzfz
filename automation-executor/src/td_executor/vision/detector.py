"""OpenCV 模板匹配检测器：支持界面状态检测、格子状态检测、错误提示检测。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from td_executor.runtime.capture import ScreenCapture
    from td_executor.runtime.window import WindowRect

logger = logging.getLogger(__name__)


@dataclass
class DetectorConfig:
    match_threshold: float = 0.8
    multi_frame_count: int = 3
    multi_frame_interval_ms: int = 100
    templates_dir: str = "assets/templates"


def crop_roi(frame: np.ndarray, roi: dict) -> np.ndarray:
    x = int(frame.shape[1] * roi["x_ratio"])
    y = int(frame.shape[0] * roi["y_ratio"])
    w = int(frame.shape[1] * roi["w_ratio"])
    h = int(frame.shape[0] * roi["h_ratio"])
    x = max(0, min(x, frame.shape[1]))
    y = max(0, min(y, frame.shape[0]))
    w = min(w, frame.shape[1] - x)
    h = min(h, frame.shape[0] - y)
    return frame[y : y + h, x : x + w]


def _load_template(template_path: str) -> np.ndarray | None:
    try:
        import cv2
    except ImportError:
        logger.warning("cv2 不可用，无法加载模板: %s", template_path)
        return None
    p = Path(template_path)
    if not p.is_file():
        logger.warning("模板文件不存在: %s", template_path)
        return None
    img = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if img is None:
        logger.warning("cv2.imread 返回 None: %s", template_path)
    return img


def _match_single(frame: np.ndarray, template: np.ndarray, threshold: float) -> bool:
    import cv2

    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold


class VisionDetector:
    def __init__(self, config: DetectorConfig | None = None) -> None:
        self._config = config or DetectorConfig()
        try:
            import cv2  # noqa: F401

            self._cv2_available = True
        except ImportError:
            self._cv2_available = False
            logger.warning("cv2 未安装，模板匹配功能不可用")

    def match_template(
        self,
        capture: ScreenCapture,
        rect: WindowRect,
        roi: dict,
        template_path: str,
        threshold: float | None = None,
    ) -> bool:
        if not self._cv2_available:
            logger.warning("cv2 不可用，match_template 返回 False")
            return False
        if threshold is None:
            threshold = self._config.match_threshold
        frame = capture.capture_frame()
        cropped = crop_roi(frame, roi)
        template = _load_template(template_path)
        if template is None:
            return False
        if self._config.multi_frame_count <= 1:
            return _match_single(cropped, template, threshold)
        match_count = 0
        for i in range(self._config.multi_frame_count):
            if i > 0:
                time.sleep(self._config.multi_frame_interval_ms / 1000.0)
            frame = capture.capture_frame()
            cropped = crop_roi(frame, roi)
            if _match_single(cropped, template, threshold):
                match_count += 1
        return match_count > self._config.multi_frame_count // 2

    def is_map_ui_open(self, capture: ScreenCapture, rect: WindowRect, rois: dict) -> bool:
        if "map_ui_indicator" not in rois:
            logger.warning("rois 中缺少 map_ui_indicator")
            return False
        template_path = str(Path(self._config.templates_dir) / "map_ui_indicator.png")
        return self.match_template(capture, rect, rois["map_ui_indicator"], template_path)

    def is_slot_empty(self, capture: ScreenCapture, rect: WindowRect, slot_verify: dict) -> bool:
        if "check_area" not in slot_verify:
            logger.warning("slot_verify 中缺少 check_area")
            return False
        template_path = str(Path(self._config.templates_dir) / "slot_empty.png")
        return self.match_template(capture, rect, slot_verify["check_area"], template_path)

    def is_slot_occupied(self, capture: ScreenCapture, rect: WindowRect, slot_verify: dict) -> bool:
        if "check_area" not in slot_verify:
            logger.warning("slot_verify 中缺少 check_area")
            return False
        template_path = str(Path(self._config.templates_dir) / "slot_occupied.png")
        return self.match_template(capture, rect, slot_verify["check_area"], template_path)

    def detect_error_tip(self, capture: ScreenCapture, rect: WindowRect, rois: dict) -> bool:
        if "place_error_tip" not in rois:
            logger.warning("rois 中缺少 place_error_tip")
            return False
        template_path = str(Path(self._config.templates_dir) / "place_error_tip.png")
        return self.match_template(capture, rect, rois["place_error_tip"], template_path)
