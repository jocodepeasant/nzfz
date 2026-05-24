"""执行器 UI Worker：Observe-Decide-Act 最小闭环（P2-07）。"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal, Slot

from nzfz_executor.core.actions.models import ClickAction
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.ui.workers.stop_token import StopToken


class ExecutorWorker(QObject):
    """后台执行 Observe-Decide-Act 任务。"""

    completed = Signal(int)
    stopped = Signal(int)
    failed = Signal(int, str)
    log = Signal(int, str)
    progress = Signal(int, int, str)

    def __init__(
        self,
        execution_id: int,
        runtime_context: ExecutorRuntimeContext | None,
        stop_token: StopToken,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._execution_id = execution_id
        self._runtime_context = runtime_context
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

            ctx = self._runtime_context
            max_iterations = max(1, ctx.max_iterations)
            loop_interval_ms = max(0, ctx.loop_interval_ms)

            self._emit_log("执行任务已启动")
            self._emit_progress(0, "执行任务已启动")

            for index in range(max_iterations):
                if self._check_stop_and_emit():
                    return

                iteration = index + 1
                base_percent = int(index / max_iterations * 100)

                self._emit_log(f"开始第 {iteration} 轮执行")
                self._emit_progress(base_percent, f"开始第 {iteration} 轮执行")

                self._run_one_iteration(iteration=iteration, total=max_iterations)

                if self._check_stop_and_emit():
                    return

                self._emit_log(f"第 {iteration} 轮执行完成")

                if index < max_iterations - 1:
                    time.sleep(loop_interval_ms / 1000)

            self._emit_progress(100, "任务执行完成")
            self._emit_log("执行任务已完成")
            self.completed.emit(self._execution_id)

        except Exception as exc:
            self.failed.emit(self._execution_id, str(exc))

    def _run_one_iteration(self, iteration: int, total: int) -> None:
        ctx = self._runtime_context
        if ctx is None:
            raise RuntimeError("执行上下文为空")

        self._emit_progress(
            self._iteration_percent(iteration, total, 10),
            "正在截图...",
        )
        self._emit_log("正在截图...")

        screenshot = ctx.screenshot_manager.capture(ctx.connected_context)

        if screenshot is None or not screenshot.success or screenshot.image is None:
            message = (
                screenshot.message
                if screenshot is not None and screenshot.message
                else "返回结果为空"
            )
            raise RuntimeError(f"截图失败：{message}")

        image = screenshot.image
        width, height = image.size

        self._emit_log(f"截图成功：{width}x{height}")

        if self._check_stop_and_emit():
            return

        self._emit_progress(
            self._iteration_percent(iteration, total, 40),
            "正在识别目标...",
        )
        self._emit_log("正在识别目标...")

        recognition = ctx.recognizer.recognize(image)

        if not recognition.found or not recognition.candidates:
            message = recognition.message or "未识别到目标，本轮跳过动作"
            self._emit_log(message)
            self._emit_progress(
                self._iteration_percent(iteration, total, 80),
                "未识别到目标，跳过动作",
            )
            return

        candidate = recognition.candidates[0]

        self._emit_log(
            "识别到目标："
            f"{candidate.name}, "
            f"image=({candidate.point.x},{candidate.point.y}), "
            f"confidence={candidate.confidence:.2f}",
        )

        if self._check_stop_and_emit():
            return

        screen_point = ctx.coordinate_mapper.image_to_screen(
            ctx.connected_context,
            candidate.point,
        )

        self._emit_log(
            "坐标映射："
            f"image=({candidate.point.x},{candidate.point.y}) "
            f"-> screen=({screen_point.x},{screen_point.y})",
        )

        if self._check_stop_and_emit():
            return

        self._emit_progress(
            self._iteration_percent(iteration, total, 70),
            "正在执行动作...",
        )

        action = ClickAction(point=screen_point)
        result = ctx.mouse_controller.click(action)

        if not result.success:
            raise RuntimeError(result.message or "动作执行失败")

        self._emit_log(result.message or "动作执行成功")

        self._emit_progress(
            self._iteration_percent(iteration, total, 95),
            f"第 {iteration} 轮动作完成",
        )

    def _check_stop_and_emit(self) -> bool:
        if self._stop_token.is_stop_requested():
            if not self._stop_notified:
                self._emit_log("任务收到停止请求")
                self.stopped.emit(self._execution_id)
                self._stop_notified = True
            return True
        return False

    def _emit_log(self, message: str) -> None:
        self.log.emit(self._execution_id, message)

    def _emit_progress(self, percent: int, message: str) -> None:
        self.progress.emit(self._execution_id, percent, message)

    def _iteration_percent(
        self,
        iteration: int,
        total: int,
        inner_percent: int,
    ) -> int:
        total = max(1, total)
        iteration = max(1, iteration)
        inner_percent = max(0, min(100, inner_percent))

        return int(((iteration - 1) + inner_percent / 100) / total * 100)
