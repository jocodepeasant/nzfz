"""视觉识别数据模型（P2-07）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePoint:
    """截图图像坐标。"""

    x: int
    y: int


@dataclass(frozen=True)
class TargetCandidate:
    """识别候选目标。"""

    name: str
    point: ImagePoint
    confidence: float


@dataclass(frozen=True)
class RecognitionResult:
    """一次识别结果。"""

    found: bool
    candidates: list[TargetCandidate]
    message: str = ""
