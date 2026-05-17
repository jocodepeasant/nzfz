from __future__ import annotations

import numpy as np


def crop_roi(frame: np.ndarray, roi: dict) -> np.ndarray:
    x = int(frame.shape[1] * roi["x_ratio"])
    y = int(frame.shape[0] * roi["y_ratio"])
    w = int(frame.shape[1] * roi["w_ratio"])
    h = int(frame.shape[0] * roi["h_ratio"])
    x = max(0, min(x, frame.shape[1]))
    y = max(0, min(y, frame.shape[0]))
    w = min(w, frame.shape[1] - x)
    h = min(h, frame.shape[0] - y)
    return frame[y : y + h, x : x + w]
