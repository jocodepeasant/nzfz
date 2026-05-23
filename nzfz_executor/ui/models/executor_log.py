"""执行器 UI 日志模型（P2-06）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ExecutorLogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ExecutorLogEntry:
    timestamp: datetime
    level: ExecutorLogLevel
    message: str
    execution_id: int | None = None
    step: str | None = None
