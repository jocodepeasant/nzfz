"""比例坐标到像素坐标（占位）。"""


def ratio_to_pixel(
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
) -> tuple[int, int]:
    """Convert region_screen_ratio to client/window coordinates."""
    x = int(window_left + window_width * x_ratio)
    y = int(window_top + window_height * y_ratio)
    return x, y
