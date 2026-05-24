"""执行器 UI 运行状态枚举（P2-04）。"""

from __future__ import annotations

from enum import Enum


class ExecutorRunState(str, Enum):
    """游戏连接页执行器运行状态，与引擎 LifecycleState 独立。"""

    NOT_READY = "not_ready"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
