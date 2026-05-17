"""OCR 引擎封装：基于 PaddleOCR 的数字识别。"""

from __future__ import annotations

import collections
import logging
import re
import threading
import time
from typing import Any

import numpy as np

from td_executor.runtime.capture import ScreenCapture
from td_executor.runtime.window import WindowRect
from td_executor.vision.utils import crop_roi

logger = logging.getLogger(__name__)

_OCR_UNAVAILABLE = object()

_ocr_engine: Any | None = None
_ocr_lock = threading.Lock()


def reset_ocr_engine() -> None:
    global _ocr_engine
    with _ocr_lock:
        _ocr_engine = None


def _preprocess_for_digits(img: np.ndarray) -> np.ndarray:
    try:
        import cv2
    except ImportError:
        logger.warning("cv2 不可用，跳过数字预处理")
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return thresh


def _get_ocr_engine() -> Any | None:
    global _ocr_engine
    if _ocr_engine is _OCR_UNAVAILABLE:
        return None
    if _ocr_engine is not None:
        return _ocr_engine
    with _ocr_lock:
        if _ocr_engine is _OCR_UNAVAILABLE:
            return None
        if _ocr_engine is not None:
            return _ocr_engine
        try:
            from paddleocr import PaddleOCR

            _ocr_engine = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            return _ocr_engine
        except Exception:
            logger.warning("PaddleOCR 初始化失败，OCR 功能不可用")
            _ocr_engine = _OCR_UNAVAILABLE
            return None


def _ocr_digits(img: np.ndarray) -> str:
    engine = _get_ocr_engine()
    if engine is None:
        return ""
    try:
        results = engine.ocr(img, cls=False)
    except Exception:
        logger.warning("OCR 识别异常")
        return ""
    if not results:
        return ""
    texts: list[str] = []
    for line in results:
        if line is None:
            continue
        for item in line:
            if item and len(item) >= 2:
                texts.append(str(item[1][0]))
    full_text = "".join(texts)
    digits = re.findall(r"\d+", full_text)
    if not digits:
        return ""
    return "".join(digits)


def read_digits_roi(
    capture: ScreenCapture,
    rect: WindowRect,
    roi: dict,
    keyword: str = "",
) -> str:
    frame = capture.capture_frame()
    sub = crop_roi(frame, roi)
    processed = _preprocess_for_digits(sub)
    result = _ocr_digits(processed)
    if keyword:
        logger.debug("OCR [%s]: '%s'", keyword, result)
    return result


def _majority_vote(results: list[str]) -> str | None:
    if not results:
        return None
    counter = collections.Counter(results)
    return counter.most_common(1)[0][0]


def _read_int_field(
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    roi_key: str,
    multi_frame_key: str,
    multi_frame: dict | None = None,
) -> int | None:
    roi = rois.get(roi_key)
    if roi is None:
        return None
    if multi_frame is not None and multi_frame_key in multi_frame:
        n_frames = multi_frame[multi_frame_key]
        results: list[str] = []
        for _ in range(n_frames):
            results.append(read_digits_roi(capture, rect, roi, keyword=roi_key))
            time.sleep(0.05)
        voted = _majority_vote(results)
    else:
        voted = read_digits_roi(capture, rect, roi, keyword=roi_key)
    if voted is None or voted == "":
        return None
    try:
        return int(voted)
    except ValueError:
        return None


def read_wave(
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    multi_frame: dict | None = None,
) -> int | None:
    return _read_int_field(capture, rect, rois, "wave", "wave_frames", multi_frame)


def read_resource(
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    multi_frame: dict | None = None,
) -> int | None:
    return _read_int_field(capture, rect, rois, "resource", "resource_frames", multi_frame)


def read_core_hp(
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    multi_frame: dict | None = None,
) -> int | None:
    return _read_int_field(capture, rect, rois, "core_hp", "core_hp_frames", multi_frame)
