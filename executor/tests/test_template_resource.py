"""P2-09 TemplateResource 单元测试。"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from nzfz_executor.core.vision.templates import TemplateResource


class TestTemplateResource:
    def test_fields(self) -> None:
        image = np.zeros((20, 30), dtype=np.uint8)
        resource = TemplateResource(
            name="start_button",
            path=Path("resources/templates/start_button.png"),
            image=image,
            width=30,
            height=20,
            threshold=0.85,
        )

        assert resource.name == "start_button"
        assert resource.width == 30
        assert resource.height == 20
        assert resource.threshold == 0.85

    def test_threshold(self) -> None:
        resource = TemplateResource(
            name="btn",
            path=Path("btn.png"),
            image=np.zeros((10, 10), dtype=np.uint8),
            width=10,
            height=10,
            threshold=0.9,
        )

        assert resource.threshold == 0.9

    def test_name_from_stem_convention(self) -> None:
        resource = TemplateResource(
            name="confirm_button",
            path=Path("resources/templates/confirm_button.png"),
            image=np.zeros((5, 5), dtype=np.uint8),
            width=5,
            height=5,
            threshold=0.85,
        )

        assert resource.name == "confirm_button"
