"""对局状态管理。"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class GameState:
    wave: int | None = None
    resource: int | None = None
    core_hp: int | None = None
    in_map_ui: bool = False
    current_region_id: str | None = None
    executed_waves: set[int] = field(default_factory=set)
    trap_levels: dict[str, int] = field(default_factory=dict)
    slot_occupied: dict[str, bool] = field(default_factory=dict)
    on_wave_changed: list[Callable[[int | None, int | None], None]] = field(default_factory=list)

    def update_wave(self, wave: int) -> bool:
        old = self.wave
        if old == wave:
            return False
        self.wave = wave
        for cb in self.on_wave_changed:
            cb(old, wave)
        return True

    def update_resource(self, resource: int) -> None:
        self.resource = resource

    def update_core_hp(self, hp: int) -> None:
        self.core_hp = hp

    def update_map_ui(self, in_map: bool) -> None:
        self.in_map_ui = in_map

    def update_region(self, region_id: str | None) -> None:
        self.current_region_id = region_id

    def update_trap_level(self, trap_id: str, level: int) -> None:
        self.trap_levels[trap_id] = level

    def update_slot_occupied(self, slot_id: str, occupied: bool) -> None:
        self.slot_occupied[slot_id] = occupied

    def mark_wave_executed(self, wave: int) -> None:
        self.executed_waves.add(wave)

    def is_wave_executed(self, wave: int) -> bool:
        return wave in self.executed_waves

    def reset(self) -> None:
        self.wave = None
        self.resource = None
        self.core_hp = None
        self.in_map_ui = False
        self.current_region_id = None
        self.executed_waves.clear()
        self.trap_levels.clear()
        self.slot_occupied.clear()
        self.on_wave_changed.clear()
