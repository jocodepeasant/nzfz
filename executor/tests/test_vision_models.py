"""P2-07 视觉模型单元测试。"""

from __future__ import annotations

from nzfz_executor.core.vision.models import (
    ImagePoint,
    RecognitionResult,
    TargetCandidate,
)


class TestVisionModels:
    def test_image_point(self) -> None:
        point = ImagePoint(x=10, y=20)
        assert point.x == 10
        assert point.y == 20

    def test_target_candidate(self) -> None:
        candidate = TargetCandidate(
            name="center",
            point=ImagePoint(x=50, y=50),
            confidence=1.0,
        )
        assert candidate.name == "center"
        assert candidate.point.x == 50
        assert candidate.confidence == 1.0

    def test_recognition_result_found(self) -> None:
        candidate = TargetCandidate(
            name="center",
            point=ImagePoint(x=1, y=2),
            confidence=1.0,
        )
        result = RecognitionResult(found=True, candidates=[candidate])
        assert result.found is True
        assert len(result.candidates) == 1

    def test_recognition_result_not_found(self) -> None:
        result = RecognitionResult(found=False, candidates=[])
        assert result.found is False
        assert result.candidates == []
