from __future__ import annotations


def ratio_to_pixel(
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
) -> tuple[int, int]:
    x = int(window_left + window_width * x_ratio)
    y = int(window_top + window_height * y_ratio)
    return x, y


def ratio_to_pixel_clamped(
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
) -> tuple[int, int]:
    x, y = ratio_to_pixel(
        window_left, window_top, window_width, window_height,
        x_ratio, y_ratio,
    )
    x = max(window_left, min(x, window_left + window_width - 1))
    y = max(window_top, min(y, window_top + window_height - 1))
    return x, y


def ratio_rect_to_pixel(
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
    w_ratio: float,
    h_ratio: float,
) -> tuple[int, int, int, int]:
    x = int(window_left + window_width * x_ratio)
    y = int(window_top + window_height * y_ratio)
    w = int(window_width * w_ratio)
    h = int(window_height * h_ratio)
    return x, y, w, h


def ratio_rect_to_pixel_clamped(
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
    w_ratio: float,
    h_ratio: float,
) -> tuple[int, int, int, int]:
    x, y, w, h = ratio_rect_to_pixel(
        window_left, window_top, window_width, window_height,
        x_ratio, y_ratio, w_ratio, h_ratio,
    )
    right = window_left + window_width
    bottom = window_top + window_height
    x = max(window_left, min(x, right - 1))
    y = max(window_top, min(y, bottom - 1))
    w = min(w, right - x)
    h = min(h, bottom - y)
    return x, y, w, h
