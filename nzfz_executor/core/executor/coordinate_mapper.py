"""截图坐标到屏幕坐标映射（P2-07 / P2-10）。"""

from __future__ import annotations

from nzfz_executor.core.actions.models import ScreenPoint
from nzfz_executor.core.models import ConnectedWindow, WindowRect
from nzfz_executor.core.scripts.models import RatioPoint, RatioRect
from nzfz_executor.core.vision.models import ImagePoint


class CoordinateMapper:
    """将截图图像坐标或 viewport ratio 映射为屏幕坐标。"""

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

    def ratio_to_screen_point(
        self,
        viewport_rect: WindowRect,
        point: RatioPoint,
    ) -> ScreenPoint:
        return ScreenPoint(
            x=int(viewport_rect.left + viewport_rect.width * point.x_ratio),
            y=int(viewport_rect.top + viewport_rect.height * point.y_ratio),
        )

    def ratio_to_screen_rect(
        self,
        viewport_rect: WindowRect,
        rect: RatioRect,
    ) -> WindowRect:
        left = int(viewport_rect.left + viewport_rect.width * rect.x_ratio)
        top = int(viewport_rect.top + viewport_rect.height * rect.y_ratio)
        right = left + int(viewport_rect.width * rect.w_ratio)
        bottom = top + int(viewport_rect.height * rect.h_ratio)
        return WindowRect(left=left, top=top, right=right, bottom=bottom)
