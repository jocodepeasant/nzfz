"""执行引擎：脚本执行的主入口，负责加载脚本、控制生命周期及驱动运行循环。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nzfz_executor.actions import register_builtin_handlers
from nzfz_executor.conditions.base import ConditionRegistry
from nzfz_executor.conditions.evaluator import ConditionEvaluator
from nzfz_executor.context import ExecutionContext
from nzfz_executor.core.dispatcher import ActionDispatcher
from nzfz_executor.core.pipeline import ExecutionPipeline
from nzfz_executor.core.scheduler import WaveScheduler
from nzfz_executor.errors import ScriptValidationError
from nzfz_executor.retry.manager import RetryManager
from nzfz_executor.script.loader import ScriptLoader
from nzfz_executor.script.validator import ScriptValidator

if TYPE_CHECKING:
    from nzfz_executor.config import ExecutorConfig
    from nzfz_executor.core.models import ConnectedWindow
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
        self._config = config
        self._event_bus = event_bus
        self._lifecycle = lifecycle_manager
        self._script_data: dict[str, Any] = {}
        self._context = ExecutionContext(config=config)

        register_builtin_handlers()
        self._dispatcher = ActionDispatcher()
        self._condition_evaluator = ConditionEvaluator(ConditionRegistry())
        self._retry_manager = RetryManager()
        self._pipeline = ExecutionPipeline(
            self._dispatcher,
            self._condition_evaluator,
            self._retry_manager,
            self._event_bus,
        )
        self._scheduler = WaveScheduler(self._pipeline, self._event_bus)

    @property
    def context(self) -> ExecutionContext:
        return self._context

    @property
    def script_data(self) -> dict[str, Any]:
        return self._script_data

    def load_script(self, path: Path | str) -> None:
        loader = ScriptLoader()
        data = loader.load(Path(path))
        validator = ScriptValidator(self._config.schema_path)
        errors = validator.validate(data)
        if errors:
            raise ScriptValidationError(errors)
        self._script_data = data
        self._context.script_data = data
        logger.info("脚本加载成功: %s", Path(path).resolve())

    def bind_connected_window(self, connected: ConnectedWindow) -> None:
        self._context.set_window_from_connected(connected)

    def start(self) -> None:
        self._lifecycle.start()
        self._run_loop()

    def pause(self) -> None:
        self._lifecycle.pause()

    def resume(self) -> None:
        self._lifecycle.resume()

    def stop(self) -> None:
        self._lifecycle.stop()

    def _run_loop(self) -> None:
        if not self._script_data:
            logger.warning("未加载脚本，跳过执行")
            return
        waves = self._script_data.get("waves") or []
        logger.info("开始执行脚本，波次数: %d", len(waves))
        self._scheduler.schedule(waves, self._context)
        if self._lifecycle.is_running:
            self._lifecycle.stop()
        logger.info("脚本执行完成")
