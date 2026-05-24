"""识别器工厂（P2-09）。"""

from __future__ import annotations

from pathlib import Path

from nzfz_executor.core.vision.recognizers import (
    CenterPointRecognizer,
    ImageRecognizer,
)
from nzfz_executor.core.vision.template_loader import TemplateLoader
from nzfz_executor.core.vision.template_matcher import TemplateMatcherRecognizer


def create_recognizer(
    recognizer_type: str,
    template_dir: str | Path,
    threshold: float,
    grayscale: bool = True,
    extensions: tuple[str, ...] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
    ),
) -> ImageRecognizer:
    normalized_type = recognizer_type.strip().lower()

    if normalized_type == "template":
        loader = TemplateLoader(
            template_dir=template_dir,
            threshold=threshold,
            grayscale=grayscale,
            extensions=extensions,
        )
        templates = loader.load_all()

        return TemplateMatcherRecognizer(
            templates=templates,
            grayscale=grayscale,
        )

    return CenterPointRecognizer()
