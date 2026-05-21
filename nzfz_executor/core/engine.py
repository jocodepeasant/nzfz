"""执行引擎：脚本执行的主入口，负责加载脚本、控制生命周期及驱动运行循环。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nzfz_executor.config import ExecutorConfig
    from nzfz_executor.events import EventBus
    from nzfz_executor.lifecycle import LifecycleManager

logger = logging.getLogger(__name__)


class ExecutorEngine:
    """执行引擎：脚本执行的主引擎，协调配置、事件总线与生命周期管理。"""

    def __init__(
        self,
        config: ExecutorConfig,
        event_bus: EventBus,
        lifecycle_manager: LifecycleManager,
    ) -> None:
        """初始化执行引擎。

        Args:
            config: 执行器全局配置。
            event_bus: 事件总线，用于组件间通信。
            lifecycle_manager: 生命周期管理器，控制状态转换。
        """
        self._config = config
        self._event_bus = event_bus
        self._lifecycle = lifecycle_manager

    def load_script(self, path: Path | str) -> None:
        """加载脚本文件。

        Args:
            path: 脚本文件路径。
        """
        pass

    def start(self) -> None:
        """启动执行引擎，进入运行状态。"""
        pass

    def pause(self) -> None:
        """暂停执行引擎。"""
        pass

    def resume(self) -> None:
        """恢复执行引擎。"""
        pass

    def stop(self) -> None:
        """停止执行引擎。"""
        pass

    def _run_loop(self) -> None:
        """内部运行循环：持续驱动脚本动作执行直到停止或完成。"""
        raise NotImplementedError