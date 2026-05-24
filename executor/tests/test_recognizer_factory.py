"""P2-09 create_recognizer 工厂单元测试。"""

from __future__ import annotations

from nzfz_executor.core.vision.recognizer_factory import create_recognizer
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.core.vision.template_matcher import TemplateMatcherRecognizer


class TestRecognizerFactory:
    def test_center_type(self) -> None:
        recognizer = create_recognizer(
            recognizer_type="center",
            template_dir="resources/templates",
            threshold=0.85,
        )

        assert isinstance(recognizer, CenterPointRecognizer)

    def test_template_type(self, tmp_path) -> None:
        recognizer = create_recognizer(
            recognizer_type="template",
            template_dir=tmp_path,
            threshold=0.85,
        )

        assert isinstance(recognizer, TemplateMatcherRecognizer)

    def test_unknown_type_falls_back_to_center(self) -> None:
        recognizer = create_recognizer(
            recognizer_type="unknown",
            template_dir="resources/templates",
            threshold=0.85,
        )

        assert isinstance(recognizer, CenterPointRecognizer)

    def test_missing_template_dir_returns_empty_matcher(self, tmp_path) -> None:
        recognizer = create_recognizer(
            recognizer_type="template",
            template_dir=tmp_path / "missing",
            threshold=0.85,
        )

        assert isinstance(recognizer, TemplateMatcherRecognizer)
        assert recognizer.templates == []

    def test_threshold_applied_to_templates(self, tmp_path) -> None:
        import cv2
        import numpy as np

        image = np.full((10, 10), 128, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "btn.png"), image)

        recognizer = create_recognizer(
            recognizer_type="template",
            template_dir=tmp_path,
            threshold=0.75,
        )

        assert isinstance(recognizer, TemplateMatcherRecognizer)
        assert recognizer.templates[0].threshold == 0.75

    def test_grayscale_passed_to_matcher(self, tmp_path) -> None:
        recognizer = create_recognizer(
            recognizer_type="template",
            template_dir=tmp_path,
            threshold=0.85,
            grayscale=False,
        )

        assert isinstance(recognizer, TemplateMatcherRecognizer)
        assert recognizer._grayscale is False
