"""P2-09 TemplateLoader 单元测试。"""

from __future__ import annotations

import cv2
import numpy as np

from nzfz_executor.core.vision.template_loader import TemplateLoader


def _write_gray_png(path, width: int, height: int, value: int = 128) -> None:
    image = np.full((height, width), value, dtype=np.uint8)
    cv2.imwrite(str(path), image)


class TestTemplateLoader:
    def test_missing_dir_returns_empty(self, tmp_path) -> None:
        loader = TemplateLoader(
            template_dir=tmp_path / "missing",
            threshold=0.85,
        )

        assert loader.load_all() == []

    def test_not_dir_returns_empty(self, tmp_path) -> None:
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("x", encoding="utf-8")

        loader = TemplateLoader(template_dir=file_path, threshold=0.85)

        assert loader.load_all() == []

    def test_empty_dir_returns_empty(self, tmp_path) -> None:
        loader = TemplateLoader(template_dir=tmp_path, threshold=0.85)

        assert loader.load_all() == []

    def test_loads_png(self, tmp_path) -> None:
        _write_gray_png(tmp_path / "a.png", 20, 10)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "a"
        assert templates[0].width == 20
        assert templates[0].height == 10

    def test_loads_jpg(self, tmp_path) -> None:
        image = np.full((10, 15), 100, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "b.jpg"), image)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "b"

    def test_loads_jpeg(self, tmp_path) -> None:
        image = np.full((10, 15), 100, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "c.jpeg"), image)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "c"

    def test_loads_bmp(self, tmp_path) -> None:
        image = np.full((10, 15), 100, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "d.bmp"), image)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "d"

    def test_skips_txt(self, tmp_path) -> None:
        (tmp_path / "skip.txt").write_text("x", encoding="utf-8")
        _write_gray_png(tmp_path / "keep.png", 10, 10)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "keep"

    def test_skips_corrupt_image(self, tmp_path) -> None:
        (tmp_path / "bad.png").write_bytes(b"not-an-image")
        _write_gray_png(tmp_path / "good.png", 10, 10)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert len(templates) == 1
        assert templates[0].name == "good"

    def test_grayscale_is_2d(self, tmp_path) -> None:
        _write_gray_png(tmp_path / "gray.png", 10, 10)

        templates = TemplateLoader(
            tmp_path,
            threshold=0.85,
            grayscale=True,
        ).load_all()

        assert templates[0].image.ndim == 2

    def test_color_is_3d(self, tmp_path) -> None:
        image = np.full((10, 10, 3), 100, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "color.png"), image)

        templates = TemplateLoader(
            tmp_path,
            threshold=0.85,
            grayscale=False,
        ).load_all()

        assert templates[0].image.ndim == 3

    def test_sorted_load_order(self, tmp_path) -> None:
        _write_gray_png(tmp_path / "z.png", 10, 10)
        _write_gray_png(tmp_path / "a.png", 10, 10)

        templates = TemplateLoader(tmp_path, threshold=0.85).load_all()

        assert [template.name for template in templates] == ["a", "z"]
