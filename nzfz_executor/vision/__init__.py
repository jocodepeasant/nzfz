"""视觉检测与 OCR 识别模块：提供模板匹配、界面状态检测及文字识别能力。"""

from nzfz_executor.vision.detector import VisionDetector
from nzfz_executor.vision.ocr import OCRReader

__all__ = ["VisionDetector", "OCRReader"]