"""P2-10 CoordinateMapper ratio 测试。"""

from __future__ import annotations

from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.models import WindowRect
from nzfz_executor.core.scripts.models import RatioPoint, RatioRect


def test_ratio_to_screen_point() -> None:
    mapper = CoordinateMapper()
    viewport = WindowRect(left=100, top=200, right=900, bottom=800)
    point = RatioPoint(x_ratio=0.5, y_ratio=0.5)

    screen = mapper.ratio_to_screen_point(viewport, point)

    assert screen.x == 500
    assert screen.y == 500


def test_ratio_to_screen_rect() -> None:
    mapper = CoordinateMapper()
    viewport = WindowRect(left=0, top=0, right=1000, bottom=1000)
    rect = RatioRect(x_ratio=0.1, y_ratio=0.2, w_ratio=0.3, h_ratio=0.4)

    screen_rect = mapper.ratio_to_screen_rect(viewport, rect)

    assert screen_rect.left == 100
    assert screen_rect.top == 200
    assert screen_rect.width == 300
    assert screen_rect.height == 400
