"""执行器 UI Worker：脚本驱动执行（P2-10）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from nzfz_executor.core.executor.options import ExecutorLaunchOptions
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.executor.script_executor import (
    ScriptExecutor,
    ScriptExecutorCallbacks,
)
from nzfz_executor.core.scripts import ScriptLoader
from nzfz_executor.ui.config.defaults import DEFAULT_SCRIPT_PATH
from nzfz_executor.ui.workers.stop_token import StopToken


def resolve_script_path(script_path: str, repo_root: Path) -> Path:
    path = Path(script_path)
    if path.is_file():
        return path
    candidate = repo_root / script_path
    if candidate.is_file():
        return candidate
    return path


class ExecutorWorker(QObject):
    """后台执行塔防脚本任务。"""

    completed = Signal(int)
    stopped = Signal(int)
    failed = Signal(int, str)
    log = Signal(int, str)
    progress = Signal(int, int, str)

    def __init__(
        self,
        execution_id: int,
        runtime_context: ExecutorRuntimeContext | None,
        launch_options: ExecutorLaunchOptions | None,
        repo_root: Path,
        stop_token: StopToken,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._execution_id = execution_id
        self._runtime_context = runtime_context
        self._launch_options = launch_options
        self._repo_root = repo_root
        self._stop_token = stop_token
        self._stop_notified = False

    @Slot()
    def run(self) -> None:
        try:
            if self._runtime_context is None:
                self.failed.emit(
                    self._execution_id,
                    "执行上下文为空，无法执行任务",
                )
                return

            options = self._launch_options or ExecutorLaunchOptions(
                script_path=DEFAULT_SCRIPT_PATH,
            )
            script_path = options.script_path or DEFAULT_SCRIPT_PATH
            resolved_path = resolve_script_path(script_path, self._repo_root)

            self._emit_log(f"[Script] 加载脚本：{resolved_path}")
            self._emit_progress(0, "正在加载脚本...")

            load_result = ScriptLoader().load(
                resolved_path,
                strict_compatibility=options.strict_compatibility,
            )
            for warning in load_result.warnings:
                self._emit_log(f"[Script] warning: {warning}")

            if not load_result.success or load_result.script is None or load_result.indexes is None:
                errors = load_result.errors or [load_result.message or "脚本加载失败"]
                message = errors[0]
                self._emit_log(f"[Script] error: {message}")
                self.failed.emit(self._execution_id, message)
                return

            self._emit_log("[Script] compatibility 校验通过")
            self._emit_progress(5, "脚本加载成功，开始执行")

            callbacks = ScriptExecutorCallbacks(
                log=self._emit_log,
                progress=self._emit_progress,
                is_stop_requested=self._stop_token.is_stop_requested,
            )
            result = ScriptExecutor().execute(
                script=load_result.script,
                indexes=load_result.indexes,
                context=self._runtime_context,
                options=options,
                callbacks=callbacks,
            )

            if result.stopped:
                if not self._stop_notified:
                    self._emit_log("任务收到停止请求")
                    self.stopped.emit(self._execution_id)
                    self._stop_notified = True
                return

            if result.success:
                self.completed.emit(self._execution_id)
                return

            self.failed.emit(
                self._execution_id,
                result.message or "脚本执行失败",
            )

        except Exception as exc:
            self.failed.emit(self._execution_id, str(exc))

    def _emit_log(self, message: str) -> None:
        self.log.emit(self._execution_id, message)

    def _emit_progress(self, percent: int, message: str) -> None:
        self.progress.emit(self._execution_id, percent, message)
