"""执行器与 GUI 的线程安全桥接。"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Callable

from td_executor.ui.events import (
    ActionCompleteEvent,
    ActionStartEvent,
    ExecutionDoneEvent,
    WaveChangeEvent,
)

logger = logging.getLogger(__name__)


class ExecutorBridge:
    def __init__(self) -> None:
        self._event_queue: queue.Queue[Any] = queue.Queue()
        self._stop_event = threading.Event()
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def get_event(self, timeout: float = 0.0) -> Any | None:
        try:
            return self._event_queue.get(block=False, timeout=timeout)
        except queue.Empty:
            return None

    def request_stop(self) -> None:
        self._stop_event.set()

    def reset(self) -> None:
        self._stop_event.clear()
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break

    def start_execution(
        self,
        script_data: dict,
        title_keyword: str = "逆战",
        dry_run: bool = False,
        on_done: Callable[[], None] | None = None,
    ) -> bool:
        if self._running:
            return False
        self.reset()
        self._running = True

        def _run():
            try:
                self._execute_script(script_data, title_keyword, dry_run)
            except Exception:
                logger.exception("Executor thread error")
            finally:
                self._running = False
                if on_done:
                    on_done()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return True

    def _execute_script(self, script_data: dict, title_keyword: str, dry_run: bool) -> None:
        from td_executor.engine.action import ActionExecutor
        from td_executor.engine.report import ActionLog, RunReport
        from td_executor.runtime.capture import ScreenCapture
        from td_executor.runtime.window import find_game_window

        script_id = script_data.get("script_id", "unknown")
        script_name = script_data.get("script_name", "unknown")
        report = RunReport(script_id=script_id, script_name=script_name, started_at=_now())

        waves = script_data.get("waves", [])
        total_waves = len(waves)
        traps = script_data.get("traps", [])
        slots = script_data.get("slots", [])
        regions = script_data.get("regions", [])
        rois = script_data.get("rois", {})
        runtime = script_data.get("runtime", {})

        rect = find_game_window(title_keyword)
        if rect is None:
            self._event_queue.put(ExecutionDoneEvent(result="error"))
            return

        capture = None
        try:
            from td_executor.runtime.capture import CaptureConfig
            capture_cfg = CaptureConfig(
                region={"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height}
            )
            capture = ScreenCapture(config=capture_cfg)
            capture.start()
        except Exception:
            logger.warning("ScreenCapture init failed, proceeding without capture")

        context: dict[str, Any] = {
            "rect": rect,
            "capture": capture,
            "rois": rois,
            "slots": slots,
            "traps": traps,
            "regions": regions,
            "runtime": runtime,
            "state": {},
        }

        executor = ActionExecutor()
        action_index = 0
        total_actions = sum(len(w.get("actions", [])) for w in waves)

        for wave_idx, wave in enumerate(waves):
            if self._stop_event.is_set():
                break
            wave_num = wave.get("wave", wave_idx + 1)
            actions = wave.get("actions", [])
            self._event_queue.put(
                WaveChangeEvent(wave=wave_num, total_waves=total_waves, wave_action_count=len(actions))
            )

            for act_idx, action in enumerate(actions):
                if self._stop_event.is_set():
                    break

                action_type = action.get("type", "")
                action_name = action.get("name", action_type)

                self._event_queue.put(
                    ActionStartEvent(
                        action_index=action_index,
                        action_type=action_type,
                        action_name=action_name,
                        wave=wave_num,
                    )
                )

                started = _now()
                result: dict[str, Any] = {"success": False, "skipped": False}

                if dry_run:
                    result = {"success": True, "skipped": False}
                else:
                    try:
                        result = executor.execute(action, context)
                    except Exception:
                        logger.exception("Action execution error")
                        result = {"success": False, "skipped": False, "error": "exception"}

                finished = _now()
                duration_ms = (finished - started).total_seconds() * 1000

                success = result.get("success", False)
                skipped = result.get("skipped", False)
                retry_count = result.get("attempts", 1) - 1 if result.get("attempts") else 0
                error_message = result.get("error")

                log_entry = ActionLog(
                    action_type=action_type,
                    action_name=action_name,
                    wave=wave_num,
                    started_at=started,
                    finished_at=finished,
                    success=success,
                    retry_count=retry_count,
                    error_message=error_message,
                )
                report.add_action(log_entry)

                self._event_queue.put(
                    ActionCompleteEvent(
                        action_index=action_index,
                        action_type=action_type,
                        action_name=action_name,
                        wave=wave_num,
                        success=success,
                        skipped=skipped,
                        retry_count=retry_count,
                        error_message=error_message,
                        duration_ms=duration_ms,
                    )
                )

                action_index += 1

        if capture:
            try:
                capture.close()
            except Exception:
                pass

        report.finished_at = _now()
        report.total_waves = total_waves

        if self._stop_event.is_set():
            report.result = "stopped"
        else:
            report.result = "completed"

        summary = report.summary()
        self._event_queue.put(
            ExecutionDoneEvent(
                result=report.result,
                total_actions=summary["total"],
                success_count=summary["success"],
                fail_count=summary["fail"],
                duration_seconds=summary["duration_seconds"] or 0.0,
            )
        )

        self._save_report(report)

    def _save_report(self, report: Any) -> None:
        from td_executor.engine.report import write_report
        from pathlib import Path

        reports_dir = Path("reports")
        timestamp = report.started_at.strftime("%Y%m%d_%H%M%S")
        path = reports_dir / f"report_{timestamp}.json"
        try:
            write_report(path, report)
            logger.info("Report saved to %s", path)
        except Exception:
            logger.exception("Failed to save report")


def _now():
    from datetime import datetime
    return datetime.now()
