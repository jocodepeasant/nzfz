"""图像识别器（P2-07）。"""

from __future__ import annotations

from typing import Protocol

from PIL import Image

from nzfz_executor.core.vision.models import (
    ImagePoint,
    RecognitionResult,
    TargetCandidate,
)


class ImageRecognizer(Protocol):
    """图像识别器协议。"""

    def recognize(self, image: Image.Image) -> RecognitionResult:
        ...


class CenterPointRecognizer:
    """返回截图中心点的最小识别器。"""

    def recognize(self, image: Image.Image) -> RecognitionResult:
        width, height = image.size

        if width <= 0 or height <= 0:
            return RecognitionResult(
                found=False,
                candidates=[],
                message="截图尺寸无效",
            )

        candidate = TargetCandidate(
            name="center",
            point=ImagePoint(
                x=width // 2,
                y=height // 2,
            ),
            confidence=1.0,
        )

        return RecognitionResult(
            found=True,
            candidates=[candidate],
            message="识别到截图中心点",
        )
