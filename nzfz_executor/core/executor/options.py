"""执行器启动参数（P2-10）。"""

from __future__ import annotations

from dataclasses import dataclass

from nzfz_executor.core.scripts.constants import (
    SCRIPT_EXECUTION_MODE_SEQUENTIAL,
)


@dataclass(frozen=True)
class ExecutorLaunchOptions:
    script_path: str
    script_execution_mode: str = SCRIPT_EXECUTION_MODE_SEQUENTIAL
    script_single_wave: int = 1
    strict_compatibility: bool = False
