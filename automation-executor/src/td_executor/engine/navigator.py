"""地图区域拖拽导航。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from td_executor.runtime.input import InputAdapter
    from td_executor.state import GameState


class Navigator:

    def __init__(
        self,
        input_adapter: InputAdapter,
        state: GameState,
        script: dict,
        wait_after_pan_ms: int = 800,
    ) -> None:
        self._input = input_adapter
        self._state = state
        self._regions = {r["region_id"]: r for r in script.get("regions", [])}
        self._wait_after_pan_ms = wait_after_pan_ms

    def pan_to_region(self, region_id: str) -> None:
        if region_id == self._state.current_region_id:
            return
        region = self._regions.get(region_id)
        if region is None:
            raise ValueError(f"未找到区域: {region_id}")
        for action in region.get("enter_actions", []):
            if action["type"] == "pan_map":
                direction = action["direction"]
                distance_ratio = action.get("distance_ratio", 0.5)
                duration_ms = action.get("duration_ms", 300)
                repeat = action.get("repeat", 1)
                start_pos, end_pos, dur = self._calculate_drag_coords(
                    direction, distance_ratio, duration_ms
                )
                for _ in range(repeat):
                    self._input.drag(
                        start_pos[0], start_pos[1],
                        end_pos[0], end_pos[1],
                        dur,
                    )
        time.sleep(self._wait_after_pan_ms / 1000)
        self._state.current_region_id = region_id

    def reset_to_origin(
        self,
        origin_region_id: str = "origin",
        wait_ms: int = 500,
    ) -> None:
        self._input.key_press("o")
        time.sleep(wait_ms / 1000)
        self._input.key_press("o")
        time.sleep(wait_ms / 1000)
        self._state.current_region_id = origin_region_id
        self._state.in_map_ui = True

    def ensure_map_ui(self, in_map_ui: bool = True) -> None:
        if in_map_ui and not self._state.in_map_ui:
            self._input.key_press("o")
            time.sleep(0.5)
            self._state.in_map_ui = True
        elif not in_map_ui and self._state.in_map_ui:
            self._input.key_press("o")
            time.sleep(0.3)
            self._state.in_map_ui = False

    def _calculate_drag_coords(
        self,
        direction: str,
        distance_ratio: float,
        duration_ms: int,
    ) -> tuple[tuple[int, int], tuple[int, int], int]:
        width = getattr(self._state, "window_width", 1920)
        height = getattr(self._state, "window_height", 1080)
        center_x = width // 2
        center_y = height // 2
        half_w = width // 2
        half_h = height // 2
        if direction == "left":
            start_x = int(center_x + distance_ratio * half_w)
            end_x = int(center_x - distance_ratio * half_w)
            start_y = center_y
            end_y = center_y
        elif direction == "right":
            start_x = int(center_x - distance_ratio * half_w)
            end_x = int(center_x + distance_ratio * half_w)
            start_y = center_y
            end_y = center_y
        elif direction == "up":
            start_x = center_x
            end_x = center_x
            start_y = int(center_y + distance_ratio * half_h)
            end_y = int(center_y - distance_ratio * half_h)
        elif direction == "down":
            start_x = center_x
            end_x = center_x
            start_y = int(center_y - distance_ratio * half_h)
            end_y = int(center_y + distance_ratio * half_h)
        else:
            raise ValueError(f"未知拖拽方向: {direction}")
        return (start_x, start_y), (end_x, end_y), duration_ms
