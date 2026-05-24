"""P2-09 TemplateMatcherRecognizer 单元测试。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from nzfz_executor.core.vision.template_matcher import TemplateMatcherRecognizer
from nzfz_executor.core.vision.templates import TemplateResource


def _template(
    *,
    name: str = "tpl",
    width: int = 20,
    height: int = 20,
    value: int = 200,
    threshold: float = 0.85,
) -> TemplateResource:
    image = np.full((height, width), value, dtype=np.uint8)
    return TemplateResource(
        name=name,
        path=Path(f"{name}.png"),
        image=image,
        width=width,
        height=height,
        threshold=threshold,
    )


def _source_with_patch(
    template: TemplateResource,
    *,
    patch_x: int = 40,
    patch_y: int = 40,
    source_size: int = 100,
) -> Image.Image:
    source = np.zeros((source_size, source_size), dtype=np.uint8)
    source[
        patch_y : patch_y + template.height,
        patch_x : patch_x + template.width,
    ] = template.image

    return Image.fromarray(
        np.stack([source, source, source], axis=-1),
    )


class TestTemplateMatcherRecognizer:
    def test_empty_templates(self) -> None:
        recognizer = TemplateMatcherRecognizer(templates=[])

        result = recognizer.recognize(Image.new("RGB", (100, 100)))

        assert result.found is False
        assert "未加载任何模板" in result.message

    def test_exact_match(self) -> None:
        template = _template()
        recognizer = TemplateMatcherRecognizer(templates=[template])
        image = _source_with_patch(template)

        result = recognizer.recognize(image)

        assert result.found is True
        assert result.candidates[0].confidence == pytest.approx(1.0, abs=0.01)

    def test_match_center_point(self) -> None:
        pattern = np.zeros((10, 20), dtype=np.uint8)
        pattern[2:8, 5:15] = 255
        template = TemplateResource(
            name="tpl",
            path=Path("tpl.png"),
            image=pattern,
            width=20,
            height=10,
            threshold=0.85,
        )
        patch_x, patch_y = 40, 30
        source = np.zeros((100, 100), dtype=np.uint8)
        source[patch_y : patch_y + 10, patch_x : patch_x + 20] = pattern
        image = Image.fromarray(
            np.stack([source, source, source], axis=-1),
        )

        recognizer = TemplateMatcherRecognizer(templates=[template])
        result = recognizer.recognize(image)

        assert result.found is True
        assert result.candidates[0].point.x == patch_x + template.width // 2
        assert result.candidates[0].point.y == patch_y + template.height // 2

    def test_below_threshold_not_found(self) -> None:
        pattern = np.zeros((20, 20), dtype=np.uint8)
        pattern[5:15, 5:15] = 255
        template = TemplateResource(
            name="tpl",
            path=Path("tpl.png"),
            image=pattern,
            width=20,
            height=20,
            threshold=0.99,
        )
        source = np.zeros((100, 100), dtype=np.uint8)
        image = Image.fromarray(
            np.stack([source, source, source], axis=-1),
        )

        recognizer = TemplateMatcherRecognizer(templates=[template])
        result = recognizer.recognize(image)

        assert result.found is False
        assert "未匹配到模板" in result.message

    def test_above_threshold_found(self) -> None:
        template = _template(threshold=0.5)
        recognizer = TemplateMatcherRecognizer(templates=[template])
        result = recognizer.recognize(_source_with_patch(template))

        assert result.found is True

    def test_multiple_templates_sorted_by_confidence(self) -> None:
        template_a = _template(name="a", value=200, threshold=0.5)
        template_b = _template(name="b", value=180, threshold=0.5)
        source = np.zeros((100, 100), dtype=np.uint8)
        source[10:30, 10:30] = template_a.image
        source[60:80, 60:80] = template_b.image
        image = Image.fromarray(
            np.stack([source, source, source], axis=-1),
        )

        recognizer = TemplateMatcherRecognizer(
            templates=[template_b, template_a],
        )
        result = recognizer.recognize(image)

        assert result.found is True
        assert len(result.candidates) == 2
        assert result.candidates[0].confidence >= result.candidates[1].confidence

    def test_template_larger_than_source_skipped(self) -> None:
        template = _template(width=120, height=120)
        recognizer = TemplateMatcherRecognizer(templates=[template])

        result = recognizer.recognize(Image.new("RGB", (100, 100)))

        assert result.found is False

    def test_grayscale_match(self) -> None:
        template = _template()
        recognizer = TemplateMatcherRecognizer(templates=[template], grayscale=True)
        result = recognizer.recognize(_source_with_patch(template))

        assert result.found is True

    def test_color_match(self) -> None:
        template = _template()
        color_template = TemplateResource(
            name=template.name,
            path=template.path,
            image=np.stack([template.image] * 3, axis=-1),
            width=template.width,
            height=template.height,
            threshold=template.threshold,
        )
        recognizer = TemplateMatcherRecognizer(
            templates=[color_template],
            grayscale=False,
        )
        result = recognizer.recognize(_source_with_patch(template))

        assert result.found is True

    def test_success_message_contains_best(self) -> None:
        template = _template(name="start_button")
        recognizer = TemplateMatcherRecognizer(templates=[template])
        result = recognizer.recognize(_source_with_patch(template))

        assert "模板匹配成功" in result.message
        assert "start_button" in result.message
