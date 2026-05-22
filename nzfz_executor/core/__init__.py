"""核心模块：提供执行引擎、动作分发、执行管线与波次调度等核心组件。"""

from nzfz_executor.core.engine import ExecutorEngine
from nzfz_executor.core.dispatcher import ActionDispatcher
from nzfz_executor.core.pipeline import ExecutionPipeline
from nzfz_executor.core.scheduler import WaveScheduler
from nzfz_executor.core.window_manager import WindowManager
from nzfz_executor.core.models import (
    WindowRect,
    WindowInfo,
    ConnectedWindow,
    HealthStatus,
    ControlMode,
    ConnectOptions,
    ConnectResult,
    HealthCheckResult,
)

__all__ = [
    "ExecutorEngine",
    "ActionDispatcher",
    "ExecutionPipeline",
    "WaveScheduler",
    "WindowManager",
    "WindowRect",
    "WindowInfo",
    "ConnectedWindow",
    "HealthStatus",
    "ControlMode",
    "ConnectOptions",
    "ConnectResult",
    "HealthCheckResult",
]