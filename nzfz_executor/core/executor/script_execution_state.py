"""脚本执行运行时状态（P2-10）。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScriptExecutionState:
    current_region_id: str | None = None
    executed_waves: set[int] = field(default_factory=set)
