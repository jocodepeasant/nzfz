"""P2-07 CoordinateMapper 单元测试。"""

from __future__ import annotations

from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.core.vision.models import ImagePoint


def _connected(window_rect: WindowRect) -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=1,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=window_rect,
        client_rect=window_rect,
    )


class TestCoordinateMapper:
    def test_offset_mapping(self) -> None:
        mapper = CoordinateMapper()
        screen = mapper.image_to_screen(
            _connected(WindowRect(100, 200, 900, 800)),
            ImagePoint(x=10, y=20),
        )

        assert screen.x == 110
        assert screen.y == 220

    def test_zero_origin(self) -> None:
        mapper = CoordinateMapper()
        screen = mapper.image_to_screen(
            _connected(WindowRect(0, 0, 800, 600)),
            ImagePoint(x=15, y=25),
        )

        assert screen.x == 15
        assert screen.y == 25

    def test_negative_window_origin(self) -> None:
        mapper = CoordinateMapper()
        screen = mapper.image_to_screen(
            _connected(WindowRect(-100, -50, 700, 550)),
            ImagePoint(x=5, y=5),
        )

        assert screen.x == -95
        assert screen.y == -45

    def test_window_rect_fields(self) -> None:
        mapper = CoordinateMapper()
        rect = WindowRect(left=10, top=20, right=810, bottom=620)
        screen = mapper.image_to_screen(
            _connected(rect),
            ImagePoint(x=3, y=4),
        )

        assert screen.x == 13
        assert screen.y == 24
