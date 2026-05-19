"""陷阱格子定位与点击。"""

from __future__ import annotations

import logging
from typing import Any

from td_executor.engine.action import click_at
from td_executor.runtime.coordinates import ratio_to_pixel
from td_executor.runtime.window import WindowRect

logger = logging.getLogger(__name__)

_micro_adjust_indices: dict[str, int] = {}


def locate_slot(slot_id: str, rect: WindowRect, slots: list[dict]) -> dict:
    for slot in slots:
        if slot.get("slot_id") == slot_id:
            position = slot.get("position", {})
            x_ratio = position.get("x_ratio", 0.0)
            y_ratio = position.get("y_ratio", 0.0)
            center_x, center_y = ratio_to_pixel(
                rect.left, rect.top, rect.width, rect.height, x_ratio, y_ratio
            )
            return {
                "slot_id": slot_id,
                "region_id": slot.get("region_id", ""),
                "center_x": center_x,
                "center_y": center_y,
                "precision": slot.get("precision", {}),
                "verify": slot.get("verify", {}),
                "slot_type": slot.get("slot_type", ""),
                "default_trap": slot.get("default_trap", ""),
            }
    logger.warning("Slot not found: %s", slot_id)
    return {}


def get_micro_adjust_points(center_x: int, center_y: int, precision: dict | None) -> list[tuple[int, int]]:
    if not precision:
        return []
    if not precision.get("allow_micro_adjust", False):
        return []
    pattern = precision.get("micro_adjust_pattern", "")
    step = precision.get("micro_adjust_step_px", 4)
    if pattern == "cross_5_points":
        return [
            (center_x, center_y),
            (center_x, center_y - step),
            (center_x, center_y + step),
            (center_x - step, center_y),
            (center_x + step, center_y),
        ]
    logger.warning("Unknown micro_adjust_pattern: %s", pattern)
    return []


def click_slot(slot_id: str, rect: WindowRect, slots: list[dict], micro_adjust: bool = False, overlay=None) -> bool:
    info = locate_slot(slot_id, rect, slots)
    if not info:
        return False
    center_x = info["center_x"]
    center_y = info["center_y"]
    precision = info.get("precision", {})
    if micro_adjust:
        points = get_micro_adjust_points(center_x, center_y, precision)
        if points:
            idx = _micro_adjust_indices.get(slot_id, 0)
            point = points[idx % len(points)]
            _micro_adjust_indices[slot_id] = (idx + 1) % len(points)
            try:
                click_at(point[0], point[1], overlay=overlay)
            except Exception:
                logger.warning("click_at failed for slot %s at (%d, %d)", slot_id, point[0], point[1])
                return False
            return True
    try:
        click_at(center_x, center_y, overlay=overlay)
    except Exception:
        logger.warning("click_at failed for slot %s at (%d, %d)", slot_id, center_x, center_y)
        return False
    return True
