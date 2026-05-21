"""执行上下文：替代无类型 dict 传递，提供类型安全的运行时信息访问。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nzfz_executor.runtime.window import WindowInfo
    from nzfz_executor.runtime.capture import ScreenCapture
    from nzfz_executor.runtime.overlay import OverlayRenderer
    from nzfz_executor.config import ExecutorConfig


@dataclass
class ExecutionState:
    """运行时状态：跟踪当前波次、陷阱等级等动态信息。"""

    current_wave: int = 0
    trap_levels: dict[str, int] = field(default_factory=dict)
    resources: int = 0
    core_hp: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """执行上下文：动作处理器执行时所需的全部运行时信息。"""

    window: WindowInfo | None = None
    capture: ScreenCapture | None = None
    overlay: OverlayRenderer | None = None
    script_data: dict[str, Any] = field(default_factory=dict)
    state: ExecutionState = field(default_factory=ExecutionState)
    config: ExecutorConfig | None = None
    action_data: dict[str, Any] = field(default_factory=dict)