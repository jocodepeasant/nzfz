"""视觉识别模块（P2-07/P2-09）。"""

from nzfz_executor.core.vision.models import (
    ImagePoint,
    RecognitionResult,
    TargetCandidate,
)
from nzfz_executor.core.vision.recognizer_factory import create_recognizer
from nzfz_executor.core.vision.recognizers import (
    CenterPointRecognizer,
    ImageRecognizer,
)
from nzfz_executor.core.vision.template_loader import TemplateLoader
from nzfz_executor.core.vision.template_matcher import TemplateMatcherRecognizer
from nzfz_executor.core.vision.templates import TemplateResource

__all__ = [
    "CenterPointRecognizer",
    "ImagePoint",
    "ImageRecognizer",
    "RecognitionResult",
    "TargetCandidate",
    "TemplateLoader",
    "TemplateMatcherRecognizer",
    "TemplateResource",
    "create_recognizer",
]
