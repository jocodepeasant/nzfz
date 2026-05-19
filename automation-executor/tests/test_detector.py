from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from td_executor.vision.detector import (
    DetectorConfig,
    VisionDetector,
    crop_roi,
    _load_template,
    _match_single,
)


class TestDetectorConfig:
    def test_defaults(self) -> None:
        cfg = DetectorConfig()
        assert cfg.match_threshold == 0.8
        assert cfg.multi_frame_count == 3
        assert cfg.multi_frame_interval_ms == 100
        assert cfg.templates_dir == "assets/templates"

    def test_custom(self) -> None:
        cfg = DetectorConfig(match_threshold=0.9, multi_frame_count=5, multi_frame_interval_ms=200, templates_dir="/tmp/tpl")
        assert cfg.match_threshold == 0.9
        assert cfg.multi_frame_count == 5
        assert cfg.multi_frame_interval_ms == 200
        assert cfg.templates_dir == "/tmp/tpl"


class TestCropRoi:
    def test_normal_crop(self) -> None:
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.42, "y_ratio": 0.03, "w_ratio": 0.12, "h_ratio": 0.04}
        result = crop_roi(frame, roi)
        expected_h = int(1080 * 0.04)
        expected_w = int(1920 * 0.12)
        assert result.shape[0] == expected_h
        assert result.shape[1] == expected_w
        assert result.shape[2] == 3

    def test_boundary_clamp(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.95, "y_ratio": 0.95, "w_ratio": 0.2, "h_ratio": 0.2}
        result = crop_roi(frame, roi)
        assert result.shape[0] > 0
        assert result.shape[1] > 0
        x = int(200 * 0.95)
        y = int(100 * 0.95)
        expected_w = min(int(200 * 0.2), 200 - x)
        expected_h = min(int(100 * 0.2), 100 - y)
        assert result.shape[0] == expected_h
        assert result.shape[1] == expected_w

    def test_zero_origin(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}
        result = crop_roi(frame, roi)
        assert result.shape[0] == 50
        assert result.shape[1] == 100


class TestLoadTemplate:
    def test_file_not_exists(self) -> None:
        result = _load_template("/nonexistent/path/template.png")
        assert result is None

    def test_cv2_not_available(self) -> None:
        with patch.dict(sys.modules, {"cv2": None}):
            result = _load_template("/some/path.png")
            assert result is None


class TestMatchSingle:
    def test_match_success(self) -> None:
        frame = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        template = frame[10:30, 20:60].copy()
        mock_cv2 = MagicMock()
        mock_cv2.TM_CCOEFF_NORMED = 5
        mock_cv2.matchTemplate.return_value = MagicMock()
        mock_cv2.minMaxLoc.return_value = (0.0, 0.95, (0, 0), (10, 20))
        with patch.dict(sys.modules, {"cv2": mock_cv2}):
            result = _match_single(frame, template, 0.8)
            assert result is True

    def test_match_failure(self) -> None:
        frame = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        template = np.random.randint(0, 255, (20, 40, 3), dtype=np.uint8)
        mock_cv2 = MagicMock()
        mock_cv2.TM_CCOEFF_NORMED = 5
        mock_cv2.matchTemplate.return_value = MagicMock()
        mock_cv2.minMaxLoc.return_value = (0.0, 0.5, (0, 0), (10, 20))
        with patch.dict(sys.modules, {"cv2": mock_cv2}):
            result = _match_single(frame, template, 0.8)
            assert result is False


class TestVisionDetectorInit:
    def test_init_default(self) -> None:
        det = VisionDetector()
        assert det._config.match_threshold == 0.8

    def test_init_with_config(self) -> None:
        cfg = DetectorConfig(match_threshold=0.9)
        det = VisionDetector(config=cfg)
        assert det._config.match_threshold == 0.9

    def test_init_cv2_available(self) -> None:
        with patch.dict(sys.modules, {"cv2": MagicMock()}):
            det = VisionDetector()
            assert det._cv2_available is True

    def test_init_cv2_not_available(self) -> None:
        with patch.dict(sys.modules, {"cv2": None}):
            det = VisionDetector()
            assert det._cv2_available is False


class TestVisionDetectorMatchTemplate:
    def _make_detector(self, multi_frame_count: int = 1) -> VisionDetector:
        cfg = DetectorConfig(multi_frame_count=multi_frame_count, templates_dir="/tmp/tpl")
        det = VisionDetector(config=cfg)
        det._cv2_available = True
        return det

    def test_single_frame_match(self) -> None:
        det = self._make_detector(multi_frame_count=1)
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture_frame.return_value = fake_frame
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.detector._load_template") as mock_load, \
             patch("td_executor.vision.detector._match_single", return_value=True):
            mock_load.return_value = np.zeros((100, 200, 3), dtype=np.uint8)
            result = det.match_template(capture, rect, roi, "/tmp/tpl/test.png")
            assert result is True

    def test_single_frame_no_match(self) -> None:
        det = self._make_detector(multi_frame_count=1)
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture_frame.return_value = fake_frame
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.detector._load_template") as mock_load, \
             patch("td_executor.vision.detector._match_single", return_value=False):
            mock_load.return_value = np.zeros((100, 200, 3), dtype=np.uint8)
            result = det.match_template(capture, rect, roi, "/tmp/tpl/test.png")
            assert result is False

    def test_template_not_found(self) -> None:
        det = self._make_detector(multi_frame_count=1)
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture_frame.return_value = fake_frame
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.detector._load_template", return_value=None):
            result = det.match_template(capture, rect, roi, "/nonexistent.png")
            assert result is False

    def test_cv2_not_available(self) -> None:
        det = self._make_detector(multi_frame_count=1)
        det._cv2_available = False
        capture = MagicMock()
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        result = det.match_template(capture, rect, roi, "/tmp/tpl/test.png")
        assert result is False

    def test_multi_frame_majority_match(self) -> None:
        det = self._make_detector(multi_frame_count=3)
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture_frame.return_value = fake_frame
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.detector._load_template") as mock_load, \
             patch("td_executor.vision.detector._match_single", side_effect=[True, False, True]), \
             patch("td_executor.vision.detector.time.sleep"):
            mock_load.return_value = np.zeros((100, 200, 3), dtype=np.uint8)
            result = det.match_template(capture, rect, roi, "/tmp/tpl/test.png")
            assert result is True

    def test_multi_frame_majority_fail(self) -> None:
        det = self._make_detector(multi_frame_count=3)
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture_frame.return_value = fake_frame
        rect = MagicMock()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.detector._load_template") as mock_load, \
             patch("td_executor.vision.detector._match_single", side_effect=[False, True, False]), \
             patch("td_executor.vision.detector.time.sleep"):
            mock_load.return_value = np.zeros((100, 200, 3), dtype=np.uint8)
            result = det.match_template(capture, rect, roi, "/tmp/tpl/test.png")
            assert result is False


class TestIsMapUiOpen:
    def _make_detector(self) -> VisionDetector:
        cfg = DetectorConfig(templates_dir="/tmp/tpl")
        det = VisionDetector(config=cfg)
        det._cv2_available = True
        return det

    def test_map_ui_open(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {"map_ui_indicator": {"x_ratio": 0.02, "y_ratio": 0.02, "w_ratio": 0.12, "h_ratio": 0.08}}
        with patch.object(det, "match_template", return_value=True):
            result = det.is_map_ui_open(capture, rect, rois)
            assert result is True

    def test_map_ui_not_open(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {"map_ui_indicator": {"x_ratio": 0.02, "y_ratio": 0.02, "w_ratio": 0.12, "h_ratio": 0.08}}
        with patch.object(det, "match_template", return_value=False):
            result = det.is_map_ui_open(capture, rect, rois)
            assert result is False

    def test_missing_map_ui_indicator(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {}
        result = det.is_map_ui_open(capture, rect, rois)
        assert result is True


class TestSlotState:
    def _make_detector(self) -> VisionDetector:
        cfg = DetectorConfig(templates_dir="/tmp/tpl")
        det = VisionDetector(config=cfg)
        det._cv2_available = True
        return det

    def test_slot_empty(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        slot_verify = {"check_area": {"x_ratio": 0.435, "y_ratio": 0.545, "w_ratio": 0.035, "h_ratio": 0.035}}
        with patch.object(det, "match_template", return_value=True):
            result = det.is_slot_empty(capture, rect, slot_verify)
            assert result is True

    def test_slot_occupied(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        slot_verify = {"check_area": {"x_ratio": 0.435, "y_ratio": 0.545, "w_ratio": 0.035, "h_ratio": 0.035}}
        with patch.object(det, "match_template", return_value=True):
            result = det.is_slot_occupied(capture, rect, slot_verify)
            assert result is True

    def test_missing_check_area(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        slot_verify = {}
        result = det.is_slot_empty(capture, rect, slot_verify)
        assert result is False
        result = det.is_slot_occupied(capture, rect, slot_verify)
        assert result is False


class TestDetectErrorTip:
    def _make_detector(self) -> VisionDetector:
        cfg = DetectorConfig(templates_dir="/tmp/tpl")
        det = VisionDetector(config=cfg)
        det._cv2_available = True
        return det

    def test_error_tip_detected(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {"place_error_tip": {"x_ratio": 0.3, "y_ratio": 0.7, "w_ratio": 0.4, "h_ratio": 0.12}}
        with patch.object(det, "match_template", return_value=True):
            result = det.detect_error_tip(capture, rect, rois)
            assert result is True

    def test_no_error_tip(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {"place_error_tip": {"x_ratio": 0.3, "y_ratio": 0.7, "w_ratio": 0.4, "h_ratio": 0.12}}
        with patch.object(det, "match_template", return_value=False):
            result = det.detect_error_tip(capture, rect, rois)
            assert result is False

    def test_missing_place_error_tip(self) -> None:
        det = self._make_detector()
        capture = MagicMock()
        rect = MagicMock()
        rois = {}
        result = det.detect_error_tip(capture, rect, rois)
        assert result is False


class TestCv2Degradation:
    def test_all_methods_return_false_without_cv2(self) -> None:
        with patch.dict(sys.modules, {"cv2": None}):
            det = VisionDetector()
            capture = MagicMock()
            rect = MagicMock()
            rois = {"map_ui_indicator": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}}
            slot_verify = {"check_area": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}}
            roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
            assert det.match_template(capture, rect, roi, "/tmp/tpl/test.png") is False
            assert det.is_map_ui_open(capture, rect, rois) is False
            assert det.is_slot_empty(capture, rect, slot_verify) is False
            assert det.is_slot_occupied(capture, rect, slot_verify) is False
            assert det.detect_error_tip(capture, rect, rois) is False
