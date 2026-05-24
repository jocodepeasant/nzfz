"""模板资源加载（P2-09）。"""

from __future__ import annotations

from pathlib import Path

import cv2

from nzfz_executor.core.vision.templates import TemplateResource


class TemplateLoader:
    """扫描模板目录并加载支持的图片文件。"""

    def __init__(
        self,
        template_dir: str | Path,
        threshold: float,
        grayscale: bool = True,
        extensions: tuple[str, ...] = (
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
        ),
    ) -> None:
        self._template_dir = Path(template_dir)
        self._threshold = threshold
        self._grayscale = grayscale
        self._extensions = tuple(
            extension.lower()
            for extension in extensions
        )

    @property
    def template_dir(self) -> Path:
        return self._template_dir

    def load_all(self) -> list[TemplateResource]:
        if not self._template_dir.exists():
            return []

        if not self._template_dir.is_dir():
            return []

        templates: list[TemplateResource] = []

        for path in sorted(self._template_dir.iterdir()):
            if not path.is_file():
                continue

            if path.suffix.lower() not in self._extensions:
                continue

            template = self._load_one(path)
            if template is not None:
                templates.append(template)

        return templates

    def _load_one(
        self,
        path: Path,
    ) -> TemplateResource | None:
        flag = cv2.IMREAD_GRAYSCALE if self._grayscale else cv2.IMREAD_COLOR
        image = cv2.imread(str(path), flag)

        if image is None:
            return None

        height, width = image.shape[:2]
        if width <= 0 or height <= 0:
            return None

        return TemplateResource(
            name=path.stem,
            path=path,
            image=image,
            width=width,
            height=height,
            threshold=self._threshold,
        )
