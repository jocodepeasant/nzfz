"""截图坐标到屏幕坐标映射（P2-07）。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import ScreenPoint
from nzfz_executor.core.models import ConnectedWindow
from nzfz_executor.core.vision.models import ImagePoint


class CoordinateMapper:
    """将截图图像坐标映射为屏幕坐标。"""

    def image_to_screen(
        self,
        context: ConnectedWindow,
        point: ImagePoint,
    ) -> ScreenPoint:
        rect = context.window_rect

        return ScreenPoint(
            x=rect.left + point.x,
            y=rect.top + point.y,
        )
