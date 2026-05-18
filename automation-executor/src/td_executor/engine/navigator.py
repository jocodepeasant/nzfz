"""地图区域拖拽导航。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from td_executor.engine.action import drag, ensure_map_open, press_key
from td_executor.runtime.window import WindowRect

if TYPE_CHECKING:
    from td_executor.runtime.capture import ScreenCapture

logger = logging.getLogger(__name__)


@dataclass
class NavigatorConfig:
    map_close_wait_ms: int = 500
    map_open_wait_ms: int = 800
    wait_after_pan_ms: int = 800


def calculate_pan_endpoints(
    rect: WindowRect,
    direction: str,
    distance_ratio: float,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    start_x = rect.left + rect.width // 2
    start_y = rect.top + rect.height // 2

    if direction == "left":
        end_x = start_x - int(rect.width * distance_ratio)
        end_y = start_y
    elif direction == "right":
        end_x = start_x + int(rect.width * distance_ratio)
        end_y = start_y
    elif direction == "up":
        end_x = start_x
        end_y = start_y - int(rect.height * distance_ratio)
    elif direction == "down":
        end_x = start_x
        end_y = start_y + int(rect.height * distance_ratio)
    else:
        logger.warning("未知拖拽方向: %s", direction)
        return None

    return (start_x, start_y), (end_x, end_y)


def go_to_origin(
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    runtime: dict,
    config: NavigatorConfig | None = None,
) -> bool:
    if config is None:
        wait_after_pan = runtime.get("wait_after_pan_ms", 800)
        config = NavigatorConfig(wait_after_pan_ms=wait_after_pan)

    try:
        if ensure_map_open(capture, rect, rois):
            try:
                press_key("o")
            except RuntimeError:
                logger.warning("press_key 不可用，无法关闭地图")
                return False
            time.sleep(config.map_close_wait_ms / 1000.0)
            try:
                press_key("o")
            except RuntimeError:
                logger.warning("press_key 不可用，无法重新打开地图")
                return False
            time.sleep(config.map_open_wait_ms / 1000.0)
            return ensure_map_open(capture, rect, rois)

        return ensure_map_open(capture, rect, rois)
    except RuntimeError:
        logger.warning("press_key 不可用，无法操作地图")
        return False


def execute_pan_action(
    action: dict,
    rect: WindowRect,
    config: NavigatorConfig | None = None,
) -> bool:
    if config is None:
        config = NavigatorConfig()

    direction = action.get("direction")
    distance_ratio = action.get("distance_ratio", 0)
    duration_ms = action.get("duration_ms", 600)
    repeat = action.get("repeat", 1)

    endpoints = calculate_pan_endpoints(rect, direction, distance_ratio)
    if endpoints is None:
        return False

    (from_x, from_y), (to_x, to_y) = endpoints

    for _ in range(repeat):
        try:
            drag(from_x, from_y, to_x, to_y, duration_ms)
        except RuntimeError:
            logger.warning("drag 不可用，无法执行拖拽")
            return False
        time.sleep(config.wait_after_pan_ms / 1000.0)

    return True


def _find_region(regions: list[dict], region_id: str) -> dict | None:
    for r in regions:
        if r.get("region_id") == region_id:
            return r
    return None


def pan_to_region(
    region_id: str,
    rect: WindowRect,
    regions: list[dict],
    capture: ScreenCapture,
    rois: dict,
    runtime: dict,
    config: NavigatorConfig | None = None,
) -> bool:
    if not go_to_origin(capture, rect, rois, runtime, config):
        return False

    region = _find_region(regions, region_id)
    if region is None:
        logger.warning("未找到区域: %s", region_id)
        return False

    enter_actions = region.get("enter_actions", [])
    for action in enter_actions:
        if action.get("type") == "pan_map":
            if not execute_pan_action(action, rect, config):
                return False

    return True
