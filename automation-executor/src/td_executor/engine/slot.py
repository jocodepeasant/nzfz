"""陷阱格子定位与微调。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from td_executor.runtime.coordinates import ratio_to_pixel
from td_executor.runtime.capture import roi_to_pixel_bounds

if TYPE_CHECKING:
    from td_executor.runtime.window import WindowRect


class SlotLocator:
    def __init__(self, script: dict, window_rect: WindowRect | None = None) -> None:
        self._slots: dict[str, dict] = {
            s["slot_id"]: s for s in script.get("slots", [])
        }
        self._window_rect = window_rect

    def _window_tuple(self) -> tuple[int, int, int, int]:
        if self._window_rect is not None:
            return (
                self._window_rect.left,
                self._window_rect.top,
                self._window_rect.width,
                self._window_rect.height,
            )
        return (0, 0, 1920, 1080)

    def locate_slot(self, slot_id: str) -> tuple[int, int]:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise ValueError(f"未找到格子: {slot_id}")
        pos = slot["position"]
        x_ratio = pos["x_ratio"]
        y_ratio = pos["y_ratio"]
        wl, wt, ww, wh = self._window_tuple()
        return ratio_to_pixel(wl, wt, ww, wh, x_ratio, y_ratio)

    def micro_adjust(
        self,
        slot_id: str,
        pattern: str = "cross_5_points",
        step_px: int = 4,
    ) -> list[tuple[int, int]]:
        cx, cy = self.locate_slot(slot_id)
        offsets: list[tuple[int, int]] = []
        if pattern == "cross_5_points":
            offsets = [
                (0, -step_px),
                (0, step_px),
                (-step_px, 0),
                (step_px, 0),
            ]
        elif pattern == "grid_9_points":
            offsets = [
                (-step_px, -step_px),
                (0, -step_px),
                (step_px, -step_px),
                (-step_px, 0),
                (step_px, 0),
                (-step_px, step_px),
                (0, step_px),
                (step_px, step_px),
            ]
        elif pattern == "spiral":
            directions = [
                (0, -1),
                (1, -1),
                (1, 0),
                (1, 1),
                (0, 1),
                (-1, 1),
                (-1, 0),
                (-1, -1),
            ]
            for multiplier in (1, 2):
                for dx, dy in directions:
                    offsets.append((dx * step_px * multiplier, dy * step_px * multiplier))
        return [(cx + dx, cy + dy) for dx, dy in offsets]

    def get_slot_config(self, slot_id: str) -> dict:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise ValueError(f"未找到格子: {slot_id}")
        return slot

    def get_slot_verify_area(self, slot_id: str) -> tuple[int, int, int, int] | None:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise ValueError(f"未找到格子: {slot_id}")
        verify = slot.get("verify")
        if not verify:
            return None
        check_area = verify.get("check_area")
        if not check_area:
            return None
        return roi_to_pixel_bounds(
            self._window_tuple(),
            check_area["x_ratio"],
            check_area["y_ratio"],
            check_area["w_ratio"],
            check_area["h_ratio"],
        )
