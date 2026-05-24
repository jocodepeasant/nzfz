"""P2-07 CenterPointRecognizer 单元测试。"""

from __future__ import annotations

from PIL import Image

from nzfz_executor.core.vision.recognizers import CenterPointRecognizer


class TestCenterPointRecognizer:
    def test_100x100_returns_center(self) -> None:
        recognizer = CenterPointRecognizer()
        result = recognizer.recognize(Image.new("RGB", (100, 100)))

        assert result.found is True
        assert result.candidates[0].point.x == 50
        assert result.candidates[0].point.y == 50

    def test_101x99_returns_center(self) -> None:
        recognizer = CenterPointRecognizer()
        result = recognizer.recognize(Image.new("RGB", (101, 99)))

        assert result.found is True
        assert result.candidates[0].point.x == 50
        assert result.candidates[0].point.y == 49

    def test_invalid_size_returns_not_found(self) -> None:
        recognizer = CenterPointRecognizer()
        result = recognizer.recognize(Image.new("RGB", (0, 100)))

        assert result.found is False
        assert result.candidates == []

    def test_confidence_is_one(self) -> None:
        recognizer = CenterPointRecognizer()
        result = recognizer.recognize(Image.new("RGB", (80, 60)))

        assert result.candidates[0].confidence == 1.0

    def test_candidate_name_is_center(self) -> None:
        recognizer = CenterPointRecognizer()
        result = recognizer.recognize(Image.new("RGB", (80, 60)))

        assert result.candidates[0].name == "center"
