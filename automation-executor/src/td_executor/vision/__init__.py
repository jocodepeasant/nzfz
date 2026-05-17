"""OCR 与图像识别。"""

from td_executor.vision.detector import DetectorConfig, VisionDetector
from td_executor.vision.utils import crop_roi

__all__ = [
    "DetectorConfig",
    "VisionDetector",
    "crop_roi",
]
