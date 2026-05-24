"""OpenCV 模板匹配识别器（P2-09）。"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from nzfz_executor.core.vision.models import (
    ImagePoint,
    RecognitionResult,
    TargetCandidate,
)
from nzfz_executor.core.vision.templates import TemplateResource


class TemplateMatcherRecognizer:
    """在截图中查找模板并返回匹配候选。"""

    def __init__(
        self,
        templates: list[TemplateResource],
        grayscale: bool = True,
    ) -> None:
        self._templates = templates
        self._grayscale = grayscale

    @property
    def templates(self) -> list[TemplateResource]:
        return self._templates

    def recognize(self, image: Image.Image) -> RecognitionResult:
        if not self._templates:
            return RecognitionResult(
                found=False,
                candidates=[],
                message="未加载任何模板，跳过模板匹配",
            )

        source = self._pil_to_cv_image(image)

        source_height, source_width = source.shape[:2]

        candidates: list[TargetCandidate] = []
        best_name = ""
        best_confidence = 0.0

        for template in self._templates:
            if template.width > source_width or template.height > source_height:
                continue

            result = cv2.matchTemplate(
                source,
                template.image,
                cv2.TM_CCOEFF_NORMED,
            )

            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            confidence = float(max_val)
            if confidence > best_confidence:
                best_confidence = confidence
                best_name = template.name

            if confidence < template.threshold:
                continue

            match_x, match_y = max_loc
            center_x = int(match_x + template.width // 2)
            center_y = int(match_y + template.height // 2)

            candidates.append(
                TargetCandidate(
                    name=template.name,
                    point=ImagePoint(
                        x=center_x,
                        y=center_y,
                    ),
                    confidence=confidence,
                ),
            )

        candidates.sort(
            key=lambda candidate: candidate.confidence,
            reverse=True,
        )

        if not candidates:
            return RecognitionResult(
                found=False,
                candidates=[],
                message=(
                    "未匹配到模板："
                    f"templates={len(self._templates)}, "
                    f"best={best_name or '-'}, "
                    f"confidence={best_confidence:.3f}"
                ),
            )

        best = candidates[0]

        return RecognitionResult(
            found=True,
            candidates=candidates,
            message=(
                "模板匹配成功："
                f"templates={len(self._templates)}, "
                f"best={best.name}, "
                f"confidence={best.confidence:.3f}, "
                f"image=({best.point.x},{best.point.y})"
            ),
        )

    def _pil_to_cv_image(
        self,
        image: Image.Image,
    ) -> np.ndarray:
        rgb = np.array(image.convert("RGB"))

        if self._grayscale:
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
