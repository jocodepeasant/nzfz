"""GUI 与执行器之间的事件定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionStartEvent:
    action_index: int
    action_type: str
    action_name: str
    wave: int


@dataclass
class ActionCompleteEvent:
    action_index: int
    action_type: str
    action_name: str
    wave: int
    success: bool
    skipped: bool
    retry_count: int = 0
    error_message: str | None = None
    duration_ms: float = 0.0


@dataclass
class WaveChangeEvent:
    wave: int
    total_waves: int
    wave_action_count: int


@dataclass
class ExecutionDoneEvent:
    result: str
    total_actions: int = 0
    success_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    duration_seconds: float = 0.0
