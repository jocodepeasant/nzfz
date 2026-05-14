from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class GameState:
    wave: int | None = None
    resource: int | None = None
    core_hp: int | None = None
    map_ui_open: bool = False
    current_region_id: str = ""
    executed_waves: set[int] = field(default_factory=set)
    trap_levels: dict[str, int] = field(default_factory=dict)
    run_start_time: float = 0.0
    max_run_minutes: int = 30

    def start(self) -> None:
        self.run_start_time = time.monotonic()
        self.executed_waves.clear()
        self.trap_levels.clear()
        self.wave = None
        self.resource = None
        self.core_hp = None
        self.map_ui_open = False
        self.current_region_id = ""

    def is_timeout(self) -> bool:
        if self.run_start_time <= 0:
            return False
        elapsed = time.monotonic() - self.run_start_time
        return elapsed > self.max_run_minutes * 60

    def mark_wave_executed(self, wave: int) -> None:
        self.executed_waves.add(wave)

    def is_wave_executed(self, wave: int) -> bool:
        return wave in self.executed_waves

    def set_trap_level(self, trap_id: str, level: int) -> None:
        self.trap_levels[trap_id] = level

    def get_trap_level(self, trap_id: str) -> int:
        return self.trap_levels.get(trap_id, 0)
