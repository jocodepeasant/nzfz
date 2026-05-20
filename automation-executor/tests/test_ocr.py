from __future__ import annotations

import collections
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import td_executor.vision.ocr as ocr_mod
from td_executor.runtime.capture import ScreenCapture
from td_executor.runtime.window import WindowRect
from td_executor.vision.ocr import (
    _crop_roi,
    _majority_vote,
    _ocr_digits,
    _preprocess_for_digits,
    read_core_hp,
    read_digits_roi,
    read_resource,
    read_wave,
)


@pytest.fixture(autouse=True)
def _reset_ocr_engine():
    original = ocr_mod._ocr_engine
    ocr_mod._ocr_engine = None
    yield
    ocr_mod._ocr_engine = original


def _make_rect() -> WindowRect:
    return WindowRect(hwnd=1, left=0, top=0, width=1920, height=1080)


def _make_capture(frame: np.ndarray | None = None) -> MagicMock:
    cap = MagicMock(spec=ScreenCapture)
    if frame is None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cap.capture_frame.return_value = frame
    return cap


class TestCropRoi:
    def test_normal_crop(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.1, "y_ratio": 0.2, "w_ratio": 0.3, "h_ratio": 0.4}
        result = _crop_roi(frame, roi)
        assert result.shape[0] == 40
        assert result.shape[1] == 30

    def test_boundary_clamp(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.9, "y_ratio": 0.9, "w_ratio": 0.2, "h_ratio": 0.2}
        result = _crop_roi(frame, roi)
        assert result.shape[0] <= 100
        assert result.shape[1] <= 100
        assert result.shape[0] >= 0
        assert result.shape[1] >= 0

    def test_zero_size_roi(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.0, "h_ratio": 0.0}
        result = _crop_roi(frame, roi)
        assert isinstance(result, np.ndarray)


class TestPreprocessForDigits:
    def test_returns_processed_image(self) -> None:
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_cv2 = MagicMock()
        gray = np.zeros((50, 50), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = gray
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.THRESH_BINARY = 0
        mock_cv2.THRESH_OTSU = 8
        mock_cv2.threshold.return_value = (0, np.zeros((50, 50), dtype=np.uint8))
        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            result = _preprocess_for_digits(img)
            assert result.ndim == 2

    def test_cv2_unavailable(self) -> None:
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        with patch.dict("sys.modules", {"cv2": None}):
            result = _preprocess_for_digits(img)
            np.testing.assert_array_equal(result, img)

    def test_cv2_import_error_returns_original(self) -> None:
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        saved = __import__
        def _fake_import(name, *args, **kwargs):
            if name == "cv2":
                raise ImportError("no cv2")
            return saved(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=_fake_import):
            result = _preprocess_for_digits(img)
            np.testing.assert_array_equal(result, img)


class TestOcrDigits:
    def test_normal_recognition(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [[[None, ("Wave 5", 0.99)]]]
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == "5"

    def test_no_engine(self) -> None:
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=None):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == ""

    def test_ocr_exception(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.side_effect = Exception("OCR failed")
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == ""

    def test_empty_results(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = []
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == ""

    def test_none_results(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = None
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == ""

    def test_no_digits_in_text(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [[[None, ("abc", 0.99)]]]
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == ""

    def test_multiple_digit_groups(self) -> None:
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [[[None, ("12abc34", 0.99)]]]
        with patch("td_executor.vision.ocr._get_ocr_engine", return_value=mock_engine):
            result = _ocr_digits(np.zeros((50, 50), dtype=np.uint8))
            assert result == "1234"


class TestMajorityVote:
    def test_clear_winner(self) -> None:
        assert _majority_vote(["5", "5", "6", "5", "4"]) == "5"

    def test_tie(self) -> None:
        result = _majority_vote(["5", "6", "5", "6"])
        assert result in ("5", "6")

    def test_empty_list(self) -> None:
        assert _majority_vote([]) is None

    def test_single_item(self) -> None:
        assert _majority_vote(["7"]) == "7"


class TestReadDigitsRoi:
    def test_full_pipeline(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = _make_capture(frame)
        rect = _make_rect()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.ocr._ocr_digits", return_value="42"):
            result = read_digits_roi(cap, rect, roi)
            assert result == "42"

    def test_empty_result(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = _make_capture(frame)
        rect = _make_rect()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.ocr._ocr_digits", return_value=""):
            result = read_digits_roi(cap, rect, roi)
            assert result == ""

    def test_with_keyword(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = _make_capture(frame)
        rect = _make_rect()
        roi = {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 1.0, "h_ratio": 1.0}
        with patch("td_executor.vision.ocr._ocr_digits", return_value="5"):
            result = read_digits_roi(cap, rect, roi, keyword="wave")
            assert result == "5"


class TestReadWave:
    def test_single_frame(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"wave": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value="5"):
            result = read_wave(cap, rect, rois)
            assert result == 5

    def test_multi_frame_voting(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"wave": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", side_effect=["5", "5", "6", "5", "4"]):
            with patch("td_executor.vision.ocr.time.sleep"):
                result = read_wave(cap, rect, rois, multi_frame={"wave_frames": 5})
                assert result == 5

    def test_no_roi(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {}
        result = read_wave(cap, rect, rois)
        assert result is None

    def test_empty_string(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"wave": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value=""):
            result = read_wave(cap, rect, rois)
            assert result is None


class TestReadResource:
    def test_single_frame(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"resource": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value="1500"):
            result = read_resource(cap, rect, rois)
            assert result == 1500

    def test_multi_frame(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"resource": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", side_effect=["1500", "1500", "1600"]):
            with patch("td_executor.vision.ocr.time.sleep"):
                result = read_resource(cap, rect, rois, multi_frame={"resource_frames": 3})
                assert result == 1500

    def test_no_roi(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value="500"):
            result = read_resource(cap, rect, rois)
            assert result == 500

    def test_empty_string(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"resource": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value=""):
            result = read_resource(cap, rect, rois)
            assert result is None


class TestReadCoreHp:
    def test_single_frame(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"core_hp": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value="100"):
            result = read_core_hp(cap, rect, rois)
            assert result == 100

    def test_multi_frame(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"core_hp": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", side_effect=["100", "100", "99"]):
            with patch("td_executor.vision.ocr.time.sleep"):
                result = read_core_hp(cap, rect, rois, multi_frame={"slot_state_frames": 3})
                assert result == 100

    def test_no_roi(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {}
        result = read_core_hp(cap, rect, rois)
        assert result is None

    def test_empty_string(self) -> None:
        cap = _make_capture()
        rect = _make_rect()
        rois = {"core_hp": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5}}
        with patch("td_executor.vision.ocr.read_digits_roi", return_value=""):
            result = read_core_hp(cap, rect, rois)
            assert result is None


class TestOcrGlobalUnavailable:
    def test_all_functions_degrade_gracefully(self) -> None:
        ocr_mod._ocr_engine = ocr_mod._OCR_UNAVAILABLE
        cap = _make_capture()
        rect = _make_rect()
        rois = {
            "wave": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5},
            "resource": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5},
            "core_hp": {"x_ratio": 0.0, "y_ratio": 0.0, "w_ratio": 0.5, "h_ratio": 0.5},
        }
        assert read_digits_roi(cap, rect, rois["wave"]) == ""
        assert read_wave(cap, rect, rois) is None
        assert read_resource(cap, rect, rois) is None
        assert read_core_hp(cap, rect, rois) is None
