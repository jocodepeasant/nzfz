"""游戏连接页签：提供窗口搜索、连接、断连及健康检测的可视化交互界面。"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCloseEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QPlainTextEdit, QProgressBar,
)

from PIL import Image

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.screenshot_manager import ScreenshotManager
from nzfz_executor.core.vision.recognizers import CenterPointRecognizer
from nzfz_executor.core.window_manager import WindowManager
from nzfz_executor.core.models import (
    WindowInfo,
    HealthStatus,
    ConnectResult,
    HealthCheckResult,
    ConnectOptions,
    CaptureRegion,
    CaptureBackendType,
    CaptureOptions,
    ScreenshotResult,
)
from nzfz_executor.ui.config.defaults import (
    DEFAULT_ACTION_DRY_RUN,
    DEFAULT_EXECUTOR_LOG_TIME_FORMAT,
    DEFAULT_EXECUTOR_LOOP_INTERVAL_MS,
    DEFAULT_EXECUTOR_MAX_ITERATIONS,
    DEFAULT_EXECUTOR_PROGRESS_LOG_ENABLED,
    DEFAULT_EXECUTOR_STOP_TIMEOUT_MS,
    DEFAULT_MAX_EXECUTOR_LOG_LINES,
    DEFAULT_SCREENSHOT_TIMEOUT_MS,
)
from nzfz_executor.ui.feedback import (
    FeedbackCode,
    FeedbackLevel,
    get_feedback_level,
    get_feedback_text,
)
from nzfz_executor.ui.models.executor_log import ExecutorLogEntry, ExecutorLogLevel
from nzfz_executor.ui.states import ExecutorRunState
from nzfz_executor.ui.workers import ExecutorTaskRunner, ScreenshotTaskRunner, WindowTaskRunner

logger = logging.getLogger(__name__)

_FEEDBACK_STYLE_COLORS = {
    FeedbackLevel.INFO: "#666666",
    FeedbackLevel.SUCCESS: "#2e7d32",
    FeedbackLevel.WARNING: "#ef6c00",
    FeedbackLevel.ERROR: "#c62828",
}

SEARCH_DEBOUNCE_MS = 300
SEARCH_TIMEOUT_MS = 3000
CONNECT_TIMEOUT_MS = 5000
HEALTH_TIMEOUT_MS = 2000
SCREENSHOT_TIMEOUT_MS = DEFAULT_SCREENSHOT_TIMEOUT_MS
EXECUTOR_STOP_TIMEOUT_MS = DEFAULT_EXECUTOR_STOP_TIMEOUT_MS


class SearchUiState(str, Enum):
    """搜索区域 UI 状态。"""

    IDLE = "idle"
    SEARCHING = "searching"
    EMPTY = "empty"
    HAS_RESULT = "has_result"
    ERROR = "error"


class ConnectionUiState(str, Enum):
    """连接生命周期 UI 状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED_READY = "connected_ready"
    CONNECTED_NOT_READY = "connected_not_ready"
    CONNECTED_UNHEALTHY = "connected_unhealthy"


class GameConnectTab(QWidget):
    """游戏连接页签，提供窗口搜索、连接管理及健康监测的完整 UI。"""

    def __init__(self) -> None:
        super().__init__()

        self._window_manager = WindowManager()

        self._task_runner = WindowTaskRunner(self._window_manager, self)
        self._task_runner.search_finished.connect(self._on_search_finished)
        self._task_runner.search_failed.connect(self._on_search_failed)
        self._task_runner.connect_finished.connect(self._on_connect_finished)
        self._task_runner.connect_failed.connect(self._on_connect_failed)
        self._task_runner.health_finished.connect(self._on_health_finished)
        self._task_runner.health_failed.connect(self._on_health_failed)

        self._screenshot_manager = ScreenshotManager()
        self._screenshot_task_runner = ScreenshotTaskRunner(self._screenshot_manager, self)
        self._screenshot_task_runner.capture_finished.connect(self._on_capture_finished)
        self._screenshot_task_runner.capture_failed.connect(self._on_capture_failed)

        self._executor_task_runner = ExecutorTaskRunner(self)
        self._executor_task_runner.completed.connect(self._on_executor_completed)
        self._executor_task_runner.stopped.connect(self._on_executor_stopped)
        self._executor_task_runner.failed.connect(self._on_executor_failed)
        self._executor_task_runner.log.connect(self._on_executor_log)
        self._executor_task_runner.progress.connect(self._on_executor_progress)
        self._executor_task_runner.start_rejected.connect(self._on_executor_start_rejected)

        self._search_state = SearchUiState.IDLE
        self._connection_state = ConnectionUiState.DISCONNECTED
        self._executor_state = ExecutorRunState.NOT_READY
        self._search_message = ""
        self._connection_message = ""
        self._search_feedback_code: FeedbackCode | None = None
        self._connection_feedback_level: FeedbackLevel | None = None

        self._current_window: WindowInfo | None = None
        self._search_results: list[WindowInfo] = []

        self._search_request_id = 0
        self._active_search_request_id = 0
        self._connect_request_id = 0
        self._active_connect_request_id = 0
        self._health_request_id = 0
        self._active_health_request_id = 0

        self._connection_generation = 0
        self._connect_request_generations: dict[int, int] = {}
        self._health_request_generations: dict[int, int] = {}

        self._execution_id = 0
        self._active_execution_id: int | None = None
        self._execution_generations: dict[int, int] = {}

        self._executor_log_entries: list[ExecutorLogEntry] = []
        self._max_executor_log_lines = DEFAULT_MAX_EXECUTOR_LOG_LINES

        self._search_running = False
        self._connecting = False
        self._health_check_running = False
        self._pending_connect_window: WindowInfo | None = None

        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(SEARCH_DEBOUNCE_MS)
        self._search_debounce_timer.timeout.connect(self._trigger_debounced_search)

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(2000)
        self._health_timer.timeout.connect(self._on_health_check)

        self._search_timeout_timers: dict[int, QTimer] = {}
        self._connect_timeout_timers: dict[int, QTimer] = {}
        self._health_timeout_timers: dict[int, QTimer] = {}

        self._capture_request_id = 0
        self._active_capture_request_id = 0
        self._capture_request_generations: dict[int, int] = {}
        self._is_capturing = False
        self._last_screenshot_pixmap: QPixmap | None = None

        self._capture_timeout_timer = QTimer(self)
        self._capture_timeout_timer.setSingleShot(True)
        self._capture_timeout_timer.setInterval(SCREENSHOT_TIMEOUT_MS)
        self._capture_timeout_timer.timeout.connect(self._on_capture_timeout)

        self._executor_stop_timeout_timer = QTimer(self)
        self._executor_stop_timeout_timer.setSingleShot(True)
        self._executor_stop_timeout_timer.setInterval(EXECUTOR_STOP_TIMEOUT_MS)
        self._executor_stop_timeout_timer.timeout.connect(self._on_executor_stop_timeout)

        self._status_label: QLabel
        self._search_status_label: QLabel
        self._search_input: QLineEdit
        self._search_btn: QPushButton
        self._result_table: QTableWidget
        self._connect_btn: QPushButton
        self._disconnect_btn: QPushButton
        self._start_executor_button: QPushButton
        self._stop_executor_button: QPushButton
        self._executor_status_label: QLabel
        self._executor_progress_bar: QProgressBar
        self._executor_step_label: QLabel
        self._executor_log_text_edit: QPlainTextEdit
        self._clear_executor_log_button: QPushButton
        self._indicator: QLabel
        self._status_text: QLabel
        self._execute_status_label: QLabel
        self._window_info: QLabel
        self._screenshot_preview_label: QLabel
        self._refresh_screenshot_button: QPushButton
        self._screenshot_status_label: QLabel
        self._screenshot_meta_label: QLabel

        self._init_ui()
        self._set_search_state(SearchUiState.IDLE)
        self._set_connection_state(ConnectionUiState.DISCONNECTED)
        self._set_executor_state(ExecutorRunState.NOT_READY)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self) -> None:
        """页面销毁时停止定时器并使在途请求失效。"""
        try:
            self._search_debounce_timer.stop()
            self._stop_health_timer()
            self._invalidate_search()
            self._active_connect_request_id = 0
            self._active_health_request_id = 0
            self._connection_generation += 1
            self._clear_search_timeouts()
            self._clear_connect_timeouts()
            self._clear_health_timeouts()
            self._reset_capture_state()
            self._executor_stop_timeout_timer.stop()
            self._active_execution_id = None
            self._execution_generations.clear()
        except Exception:
            logger.debug("cleanup encountered an error", exc_info=True)

    def __del__(self) -> None:
        """析构时兜底调用清理逻辑，防止资源泄漏。"""
        try:
            self.cleanup()
        except Exception:
            pass

    def _reset_capture_state(self) -> None:
        """停止截图超时计时器并重置截图进行中状态。"""
        self._capture_timeout_timer.stop()
        self._active_capture_request_id = 0
        self._is_capturing = False
        self._update_screenshot_button_state()

    def _is_connect_result_current(
        self,
        request_id: int,
        request_generation: int | None,
    ) -> bool:
        if request_id != self._active_connect_request_id:
            return False
        if request_generation != self._connection_generation:
            return False
        return True

    def _is_health_result_current(
        self,
        request_id: int,
        request_generation: int | None,
    ) -> bool:
        if request_id != self._active_health_request_id:
            return False
        if request_generation != self._connection_generation:
            return False
        return True

    def _invalidate_search(self) -> None:
        self._search_request_id += 1
        self._active_search_request_id = self._search_request_id
        self._search_running = False

    def _invalidate_health_checks(self) -> None:
        self._health_request_id += 1
        self._active_health_request_id = self._health_request_id
        self._health_check_running = False

    def _start_search_timeout(self, request_id: int) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(SEARCH_TIMEOUT_MS)
        timer.timeout.connect(lambda rid=request_id: self._on_search_timeout(rid))
        self._search_timeout_timers[request_id] = timer
        timer.start()

    def _stop_search_timeout(self, request_id: int) -> None:
        timer = self._search_timeout_timers.pop(request_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _start_connect_timeout(self, request_id: int) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(CONNECT_TIMEOUT_MS)
        timer.timeout.connect(lambda rid=request_id: self._on_connect_timeout(rid))
        self._connect_timeout_timers[request_id] = timer
        timer.start()

    def _stop_connect_timeout(self, request_id: int) -> None:
        timer = self._connect_timeout_timers.pop(request_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _start_health_timeout(self, request_id: int) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(HEALTH_TIMEOUT_MS)
        timer.timeout.connect(lambda rid=request_id: self._on_health_timeout(rid))
        self._health_timeout_timers[request_id] = timer
        timer.start()

    def _stop_health_timeout(self, request_id: int) -> None:
        timer = self._health_timeout_timers.pop(request_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _clear_search_timeouts(self) -> None:
        for timer in self._search_timeout_timers.values():
            timer.stop()
            timer.deleteLater()
        self._search_timeout_timers.clear()

    def _clear_connect_timeouts(self) -> None:
        for timer in self._connect_timeout_timers.values():
            timer.stop()
            timer.deleteLater()
        self._connect_timeout_timers.clear()

    def _clear_health_timeouts(self) -> None:
        for timer in self._health_timeout_timers.values():
            timer.stop()
            timer.deleteLater()
        self._health_timeout_timers.clear()

    def _set_search_state(
        self,
        state: SearchUiState,
        message: str = "",
        *,
        feedback_code: FeedbackCode | None = None,
    ) -> None:
        old_state = self._search_state
        self._search_state = state
        self._search_message = message
        self._search_feedback_code = feedback_code
        if old_state != state:
            logger.info("搜索状态变更: %s → %s", old_state.value, state.value)
        self._apply_ui_state()

    def _set_connection_state(
        self,
        state: ConnectionUiState,
        message: str = "",
        *,
        feedback_level: FeedbackLevel | None = None,
    ) -> None:
        old_state = self._connection_state
        self._connection_state = state
        self._connection_message = message
        self._connection_feedback_level = feedback_level
        if old_state != state:
            logger.info("连接状态变更: %s → %s", old_state.value, state.value)
        self._on_connection_state_changed_for_executor(state)
        self._apply_ui_state()

    def _apply_feedback_style(self, label: QLabel, level: FeedbackLevel) -> None:
        color = _FEEDBACK_STYLE_COLORS.get(level, "#666666")
        label.setStyleSheet(f"color: {color};")

    def _show_search_feedback(self, code: FeedbackCode, **kwargs: object) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._search_status_label.setText(text)
        self._apply_feedback_style(self._search_status_label, level)

    def _show_connection_feedback(self, code: FeedbackCode, **kwargs: object) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._status_text.setText(text)
        self._apply_feedback_style(self._status_text, level)

    def _show_execute_feedback(self, code: FeedbackCode, **kwargs: object) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._execute_status_label.setText(text)
        self._apply_feedback_style(self._execute_status_label, level)

    def _show_executor_feedback(self, code: FeedbackCode, **kwargs: object) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._executor_status_label.setText(text)
        self._apply_feedback_style(self._executor_status_label, level)

    def _show_executor_feedback_by_state(self, state: ExecutorRunState) -> None:
        mapping = {
            ExecutorRunState.NOT_READY: FeedbackCode.EXECUTOR_NOT_READY,
            ExecutorRunState.READY: FeedbackCode.EXECUTOR_READY,
            ExecutorRunState.RUNNING: FeedbackCode.EXECUTOR_RUNNING,
            ExecutorRunState.STOPPING: FeedbackCode.EXECUTOR_STOPPING,
            ExecutorRunState.STOPPED: FeedbackCode.EXECUTOR_STOPPED,
            ExecutorRunState.COMPLETED: FeedbackCode.EXECUTOR_COMPLETED,
            ExecutorRunState.FAILED: FeedbackCode.EXECUTOR_FAILED,
        }
        self._show_executor_feedback(mapping.get(state, FeedbackCode.EXECUTOR_NOT_READY))

    def _is_executor_busy(self) -> bool:
        return self._executor_state in {
            ExecutorRunState.RUNNING,
            ExecutorRunState.STOPPING,
        }

    def _is_executor_ready(self) -> bool:
        return (
            self._connection_state == ConnectionUiState.CONNECTED_READY
            and not self._is_capturing
            and not self._is_executor_busy()
        )

    def _set_executor_state(
        self,
        state: ExecutorRunState,
        message: str | None = None,
    ) -> None:
        old_state = self._executor_state
        if self._executor_state == state and message is None:
            self._update_executor_controls()
            self._update_connection_controls_state()
            self._update_screenshot_button_state()
            self._show_executor_feedback_by_state(state)
            return

        self._executor_state = state
        if old_state != state:
            logger.info("执行器状态变更: %s → %s", old_state.value, state.value)

        if message is not None:
            self._executor_status_label.setText(message)
            self._apply_feedback_style(
                self._executor_status_label,
                FeedbackLevel.ERROR if state == ExecutorRunState.FAILED else FeedbackLevel.INFO,
            )
        else:
            self._show_executor_feedback_by_state(state)

        self._update_executor_controls()
        self._update_connection_controls_state()
        self._update_screenshot_button_state()

    def _refresh_executor_ready_state(self) -> None:
        if self._is_executor_busy():
            return
        if self._is_executor_ready():
            self._set_executor_state(ExecutorRunState.READY)
        else:
            self._set_executor_state(ExecutorRunState.NOT_READY)

    def _update_executor_controls(self) -> None:
        can_start = self._executor_state == ExecutorRunState.READY
        can_stop = self._executor_state == ExecutorRunState.RUNNING
        self._start_executor_button.setEnabled(can_start)
        self._stop_executor_button.setEnabled(can_stop)

    def _ensure_can_change_connection(self) -> bool:
        if self._is_executor_busy():
            self._show_executor_feedback(FeedbackCode.EXECUTOR_STOP_REQUIRED)
            return False
        return True

    def _on_connection_state_changed_for_executor(
        self,
        state: ConnectionUiState,
    ) -> None:
        if self._executor_state == ExecutorRunState.RUNNING:
            if state != ConnectionUiState.CONNECTED_READY:
                self._executor_task_runner.request_stop()
                self._set_executor_state(
                    ExecutorRunState.FAILED,
                    "连接状态异常，任务执行失败",
                )
                self._stop_health_timer()
                self._reset_capture_state()
                self._clear_screenshot_preview()
                self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_UNAVAILABLE)
                return
        if not self._is_executor_busy():
            self._refresh_executor_ready_state()

    def _next_execution_id(self) -> int:
        self._execution_id += 1
        return self._execution_id

    def _is_active_execution_result(self, execution_id: int) -> bool:
        if execution_id != self._active_execution_id:
            logger.debug(
                "Discard expired execution result: execution_id=%s, active=%s",
                execution_id,
                self._active_execution_id,
            )
            return False

        request_generation = self._execution_generations.get(execution_id)
        if request_generation != self._connection_generation:
            logger.debug(
                "Discard execution result due to generation mismatch: "
                "execution_id=%s, request_generation=%s, current_generation=%s",
                execution_id,
                request_generation,
                self._connection_generation,
            )
            return False

        return True

    def _format_executor_log_entry(self, entry: ExecutorLogEntry) -> str:
        timestamp = entry.timestamp.strftime(DEFAULT_EXECUTOR_LOG_TIME_FORMAT)
        level = entry.level.value.upper()
        return f"[{timestamp}] [{level}] {entry.message}"

    def _append_executor_log(
        self,
        level: ExecutorLogLevel,
        message: str,
        execution_id: int | None = None,
        step: str | None = None,
    ) -> None:
        entry = ExecutorLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            execution_id=execution_id,
            step=step,
        )
        self._executor_log_entries.append(entry)

        while len(self._executor_log_entries) > self._max_executor_log_lines:
            self._executor_log_entries.pop(0)

        self._render_executor_logs()
        self._scroll_executor_log_to_bottom()

    def _render_executor_logs(self) -> None:
        lines = [
            self._format_executor_log_entry(entry)
            for entry in self._executor_log_entries
        ]
        self._executor_log_text_edit.setPlainText("\n".join(lines))

    def _scroll_executor_log_to_bottom(self) -> None:
        scroll_bar = self._executor_log_text_edit.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def _clear_executor_logs(self) -> None:
        self._executor_log_entries.clear()
        self._executor_log_text_edit.clear()

    def _set_executor_step(self, message: str) -> None:
        self._executor_step_label.setText(f"当前步骤：{message}")

    def _update_executor_progress(self, percent: int, message: str) -> None:
        percent = max(0, min(100, percent))
        self._executor_progress_bar.setValue(percent)
        self._set_executor_step(message)

    def _reset_executor_progress(self) -> None:
        self._executor_progress_bar.setValue(0)
        self._set_executor_step("-")

    def _on_start_executor_clicked(self) -> None:
        if self._executor_state != ExecutorRunState.READY:
            self._show_executor_feedback(FeedbackCode.EXECUTOR_START_BLOCKED)
            return

        if not self._is_executor_ready():
            self._show_executor_feedback(FeedbackCode.EXECUTOR_START_BLOCKED)
            self._refresh_executor_ready_state()
            return

        context = self._window_manager.get_connected_context()
        if context is None:
            self._show_executor_feedback(FeedbackCode.EXECUTOR_START_BLOCKED)
            self._refresh_executor_ready_state()
            return

        execution_id = self._next_execution_id()
        self._active_execution_id = execution_id
        self._execution_generations[execution_id] = self._connection_generation

        self._executor_progress_bar.setValue(0)
        self._set_executor_step("准备启动执行任务")
        self._append_executor_log(
            ExecutorLogLevel.INFO,
            "准备启动执行任务",
            execution_id=execution_id,
        )

        self._set_executor_state(ExecutorRunState.RUNNING)

        runtime_context = ExecutorRuntimeContext(
            connected_context=context,
            screenshot_manager=self._screenshot_manager,
            recognizer=CenterPointRecognizer(),
            coordinate_mapper=CoordinateMapper(),
            mouse_controller=MouseController.create_default(
                dry_run=DEFAULT_ACTION_DRY_RUN,
            ),
            max_iterations=DEFAULT_EXECUTOR_MAX_ITERATIONS,
            loop_interval_ms=DEFAULT_EXECUTOR_LOOP_INTERVAL_MS,
        )

        started = self._executor_task_runner.start(
            execution_id=execution_id,
            runtime_context=runtime_context,
        )
        if not started:
            self._append_executor_log(
                ExecutorLogLevel.ERROR,
                "执行任务启动失败：当前已有任务正在运行",
                execution_id=execution_id,
            )
            self._active_execution_id = None
            self._execution_generations.pop(execution_id, None)
            self._set_executor_state(
                ExecutorRunState.FAILED,
                get_feedback_text(FeedbackCode.EXECUTOR_ALREADY_RUNNING),
            )
            self._set_executor_step("执行任务启动失败")
            self._refresh_executor_ready_state()
            return

        self._append_executor_log(
            ExecutorLogLevel.SUCCESS,
            "执行任务已启动",
            execution_id=execution_id,
        )

    def _on_stop_executor_clicked(self) -> None:
        if self._executor_state != ExecutorRunState.RUNNING:
            return

        execution_id = self._active_execution_id

        self._append_executor_log(
            ExecutorLogLevel.WARNING,
            "用户请求停止任务",
            execution_id=execution_id,
        )

        self._set_executor_state(ExecutorRunState.STOPPING)
        self._set_executor_step("正在停止任务...")
        self._executor_stop_timeout_timer.start(EXECUTOR_STOP_TIMEOUT_MS)

        accepted = self._executor_task_runner.request_stop()
        if not accepted:
            self._executor_stop_timeout_timer.stop()
            self._append_executor_log(
                ExecutorLogLevel.ERROR,
                "停止任务失败：当前没有正在运行的任务",
                execution_id=execution_id,
            )
            self._active_execution_id = None
            self._set_executor_state(
                ExecutorRunState.FAILED,
                get_feedback_text(FeedbackCode.EXECUTOR_NO_ACTIVE_TASK),
            )
            self._set_executor_step("停止任务失败")
            self._refresh_executor_ready_state()
            return

        self._append_executor_log(
            ExecutorLogLevel.INFO,
            "停止请求已发送，等待任务安全退出",
            execution_id=execution_id,
        )

    def _on_executor_completed(self, execution_id: int) -> None:
        if not self._is_active_execution_result(execution_id):
            return

        logger.info("Executor completed: execution_id=%s", execution_id)
        self._executor_stop_timeout_timer.stop()
        self._active_execution_id = None
        self._execution_generations.pop(execution_id, None)

        self._executor_progress_bar.setValue(100)
        self._set_executor_step("任务执行完成")
        self._append_executor_log(
            ExecutorLogLevel.SUCCESS,
            "任务执行完成",
            execution_id=execution_id,
        )

        self._set_executor_state(ExecutorRunState.COMPLETED)
        self._refresh_executor_ready_state()

    def _on_executor_stopped(self, execution_id: int) -> None:
        if not self._is_active_execution_result(execution_id):
            return

        logger.info("Executor stopped: execution_id=%s", execution_id)
        self._executor_stop_timeout_timer.stop()
        self._active_execution_id = None
        self._execution_generations.pop(execution_id, None)

        self._set_executor_step("任务已停止")
        self._append_executor_log(
            ExecutorLogLevel.SUCCESS,
            "任务已停止",
            execution_id=execution_id,
        )

        self._set_executor_state(ExecutorRunState.STOPPED)
        self._refresh_executor_ready_state()

    def _on_executor_failed(self, execution_id: int, message: str) -> None:
        if not self._is_active_execution_result(execution_id):
            return

        logger.warning(
            "Executor failed: execution_id=%s, message=%s",
            execution_id,
            message,
        )
        self._executor_stop_timeout_timer.stop()
        self._active_execution_id = None
        self._execution_generations.pop(execution_id, None)

        display_message = message or get_feedback_text(FeedbackCode.EXECUTOR_FAILED)
        self._set_executor_step(f"任务执行失败：{display_message}")
        self._append_executor_log(
            ExecutorLogLevel.ERROR,
            f"任务执行失败：{display_message}",
            execution_id=execution_id,
        )

        self._set_executor_state(
            ExecutorRunState.FAILED,
            display_message,
        )
        self._refresh_executor_ready_state()

    def _on_executor_log(self, execution_id: int, message: str) -> None:
        if not self._is_active_execution_result(execution_id):
            logger.debug(
                "Discard expired executor log: execution_id=%s",
                execution_id,
            )
            return

        logger.info("Executor log[%s]: %s", execution_id, message)
        self._append_executor_log(
            ExecutorLogLevel.INFO,
            message,
            execution_id=execution_id,
        )

    def _on_executor_progress(
        self,
        execution_id: int,
        percent: int,
        message: str,
    ) -> None:
        if not self._is_active_execution_result(execution_id):
            logger.debug(
                "Discard expired executor progress: execution_id=%s",
                execution_id,
            )
            return

        logger.debug(
            "Executor progress[%s]: %s%% %s",
            execution_id,
            percent,
            message,
        )
        self._update_executor_progress(percent, message)

        if DEFAULT_EXECUTOR_PROGRESS_LOG_ENABLED:
            self._append_executor_log(
                ExecutorLogLevel.INFO,
                f"{percent}% - {message}",
                execution_id=execution_id,
            )

    def _on_executor_start_rejected(
        self,
        execution_id: int,
        message: str,
    ) -> None:
        if execution_id != self._active_execution_id:
            return

        display_message = message or get_feedback_text(FeedbackCode.EXECUTOR_ALREADY_RUNNING)
        self._append_executor_log(
            ExecutorLogLevel.ERROR,
            f"执行任务启动失败：{display_message}",
            execution_id=execution_id,
        )

        self._active_execution_id = None
        self._execution_generations.pop(execution_id, None)

        self._set_executor_state(
            ExecutorRunState.FAILED,
            display_message,
        )
        self._set_executor_step("执行任务启动失败")
        self._refresh_executor_ready_state()

    def _on_executor_stop_timeout(self) -> None:
        execution_id = self._active_execution_id

        logger.warning("Executor stop timeout: execution_id=%s", execution_id)

        self._append_executor_log(
            ExecutorLogLevel.ERROR,
            get_feedback_text(FeedbackCode.EXECUTOR_STOP_TIMEOUT),
            execution_id=execution_id,
        )

        self._active_execution_id = None
        if execution_id is not None:
            self._execution_generations.pop(execution_id, None)

        self._set_executor_step("任务停止超时")
        self._set_executor_state(
            ExecutorRunState.FAILED,
            get_feedback_text(FeedbackCode.EXECUTOR_STOP_TIMEOUT),
        )
        self._refresh_executor_ready_state()

    def _show_hint_feedback(self, code: FeedbackCode, **kwargs: object) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._status_label.setText(text)
        self._apply_feedback_style(self._status_label, level)
        self._status_label.setVisible(True)

    def _resolve_search_feedback_code(self) -> FeedbackCode:
        if self._search_feedback_code is not None:
            return self._search_feedback_code
        mapping = {
            SearchUiState.IDLE: FeedbackCode.SEARCH_INPUT_REQUIRED,
            SearchUiState.SEARCHING: FeedbackCode.SEARCHING,
            SearchUiState.EMPTY: FeedbackCode.SEARCH_NO_RESULT,
            SearchUiState.HAS_RESULT: FeedbackCode.SEARCH_FOUND,
            SearchUiState.ERROR: FeedbackCode.SEARCH_FAILED,
        }
        return mapping[self._search_state]

    def _resolve_connection_feedback_code(self) -> FeedbackCode:
        mapping = {
            ConnectionUiState.DISCONNECTED: FeedbackCode.DISCONNECTED,
            ConnectionUiState.CONNECTING: FeedbackCode.CONNECTING,
            ConnectionUiState.CONNECTED_READY: FeedbackCode.CONNECT_SUCCESS_READY,
            ConnectionUiState.CONNECTED_NOT_READY: FeedbackCode.CONNECT_SUCCESS_READY,
            ConnectionUiState.CONNECTED_UNHEALTHY: FeedbackCode.HEALTH_UNHEALTHY,
        }
        return mapping[self._connection_state]

    def _resolve_execute_feedback_code(self) -> FeedbackCode:
        mapping = {
            ConnectionUiState.DISCONNECTED: FeedbackCode.HEALTH_DISCONNECTED,
            ConnectionUiState.CONNECTING: FeedbackCode.HEALTH_DISCONNECTED,
            ConnectionUiState.CONNECTED_READY: FeedbackCode.HEALTH_READY,
            ConnectionUiState.CONNECTED_NOT_READY: FeedbackCode.HEALTH_NOT_READY_FOREGROUND,
            ConnectionUiState.CONNECTED_UNHEALTHY: FeedbackCode.HEALTH_UNHEALTHY,
        }
        return mapping[self._connection_state]

    def _is_connected_state(self) -> bool:
        return self._connection_state in {
            ConnectionUiState.CONNECTED_READY,
            ConnectionUiState.CONNECTED_NOT_READY,
            ConnectionUiState.CONNECTED_UNHEALTHY,
        }

    def _get_selected_window_info(self) -> WindowInfo | None:
        selected_rows = self._result_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        if row < 0 or row >= len(self._search_results):
            return None
        return self._search_results[row]

    def _apply_ui_state(self) -> None:
        self._update_connection_controls_state()

        self._window_info.setVisible(self._is_connected_state())

        self._update_search_status_label()
        self._update_connection_status_label()
        self._update_execute_status_label()
        self._update_screenshot_button_state()

    def _update_connection_controls_state(self) -> None:
        selected_window = self._get_selected_window_info()

        is_connecting = self._connection_state == ConnectionUiState.CONNECTING
        is_searching = self._search_state == SearchUiState.SEARCHING
        executor_busy = self._is_executor_busy()

        can_connect = (
            not is_connecting
            and not is_searching
            and not executor_busy
            and self._search_state == SearchUiState.HAS_RESULT
            and selected_window is not None
            and not selected_window.is_minimized
        )

        can_disconnect = (
            not executor_busy
            and self._connection_state in {
                ConnectionUiState.CONNECTED_READY,
                ConnectionUiState.CONNECTED_NOT_READY,
                ConnectionUiState.CONNECTED_UNHEALTHY,
            }
        )

        self._search_input.setEnabled(not is_connecting and not executor_busy)
        self._search_btn.setEnabled(
            not is_connecting and not is_searching and not executor_busy,
        )
        self._result_table.setEnabled(not is_connecting and not executor_busy)

        self._connect_btn.setEnabled(can_connect)
        self._disconnect_btn.setEnabled(can_disconnect)

        self._update_executor_controls()

    def _update_search_status_label(self) -> None:
        if self._search_message:
            text = self._search_message
            level = get_feedback_level(self._resolve_search_feedback_code())
        else:
            code = self._resolve_search_feedback_code()
            kwargs: dict[str, object] = {}
            if code == FeedbackCode.SEARCH_FOUND:
                kwargs["count"] = len(self._search_results)
            text = get_feedback_text(code, **kwargs)
            level = get_feedback_level(code)
        self._search_status_label.setText(text)
        self._apply_feedback_style(self._search_status_label, level)

    def _update_connection_status_label(self) -> None:
        color_map = {
            ConnectionUiState.DISCONNECTED: "#f38ba8",
            ConnectionUiState.CONNECTING: "#f9e2af",
            ConnectionUiState.CONNECTED_READY: "#a6e3a1",
            ConnectionUiState.CONNECTED_NOT_READY: "#a6e3a1",
            ConnectionUiState.CONNECTED_UNHEALTHY: "#f9e2af",
        }

        state = self._connection_state
        color = color_map.get(state, "#f38ba8")
        self._indicator.setStyleSheet(
            f"QLabel#status_indicator {{"
            f"  background-color: {color};"
            f"  border-radius: 8px;"
            f"  min-width: 16px;"
            f"  min-height: 16px;"
            f"}}"
        )

        if self._connection_message:
            text = self._connection_message
            level = self._connection_feedback_level or FeedbackLevel.ERROR
        else:
            code = self._resolve_connection_feedback_code()
            text = get_feedback_text(code)
            level = get_feedback_level(code)
            if state == ConnectionUiState.CONNECTED_NOT_READY:
                text = "已连接"
                level = FeedbackLevel.SUCCESS

        self._status_text.setText(text)
        self._apply_feedback_style(self._status_text, level)

    def _update_execute_status_label(self) -> None:
        if (
            self._connection_message
            and self._connection_state == ConnectionUiState.CONNECTED_UNHEALTHY
        ):
            text = self._connection_message
            level = self._connection_feedback_level or FeedbackLevel.ERROR
        elif (
            self._connection_message
            and self._connection_state == ConnectionUiState.CONNECTED_NOT_READY
        ):
            text = self._connection_message
            level = self._connection_feedback_level or FeedbackLevel.WARNING
        else:
            code = self._resolve_execute_feedback_code()
            text = get_feedback_text(code)
            level = get_feedback_level(code)

        self._execute_status_label.setText(text)
        self._apply_feedback_style(self._execute_status_label, level)

    def _apply_health_result(self, result: HealthCheckResult) -> None:
        if not result.is_connected:
            self._set_connection_state(ConnectionUiState.DISCONNECTED)
            return

        if result.is_healthy and result.is_ready:
            self._set_connection_state(ConnectionUiState.CONNECTED_READY)
            return

        if result.is_healthy and not result.is_ready:
            message = result.message or get_feedback_text(
                FeedbackCode.HEALTH_NOT_READY_FOREGROUND,
            )
            self._set_connection_state(
                ConnectionUiState.CONNECTED_NOT_READY,
                message,
                feedback_level=FeedbackLevel.WARNING,
            )
            return

        message = result.message or get_feedback_text(FeedbackCode.HEALTH_UNHEALTHY)
        self._set_connection_state(
            ConnectionUiState.CONNECTED_UNHEALTHY,
            message,
            feedback_level=FeedbackLevel.ERROR,
        )

    def _confirm_switch_connection(self, window_info: WindowInfo) -> bool:
        title = get_feedback_text(FeedbackCode.CONFIRM_SWITCH_CONNECTION_TITLE)
        message = get_feedback_text(FeedbackCode.CONFIRM_SWITCH_CONNECTION_MESSAGE)
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            logger.debug("用户取消切换连接")
        return reply == QMessageBox.StandardButton.Yes

    def _disconnect_for_switch(self) -> None:
        self._stop_health_timer()

        self._active_connect_request_id = 0
        self._active_health_request_id = 0

        self._connecting = False
        self._health_check_running = False

        self._connect_request_generations.clear()
        self._health_request_generations.clear()

        self._clear_connect_timeouts()
        self._clear_health_timeouts()

        self._reset_capture_state()
        self._clear_screenshot_preview()

        self._window_manager.disconnect_window()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        layout.addLayout(self._create_search_section())
        layout.addLayout(self._create_action_section())
        layout.addLayout(self._create_status_section())
        layout.addLayout(self._create_executor_area())
        layout.addLayout(self._create_screenshot_area())
        layout.addStretch()

    def _create_search_section(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入窗口标题、进程名或 PID")
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.returnPressed.connect(self._trigger_immediate_search)
        search_row.addWidget(self._search_input)

        self._search_btn = QPushButton("搜索")
        self._search_btn.clicked.connect(self._trigger_immediate_search)
        search_row.addWidget(self._search_btn)

        section.addLayout(search_row)

        self._search_status_label = QLabel()
        section.addWidget(self._search_status_label)

        self._result_table = QTableWidget(0, 4)
        self._result_table.setHorizontalHeaderLabels(["窗口标题", "进程名", "PID", "状态"])
        self._result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._result_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._result_table.horizontalHeader().setStretchLastSection(True)
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._result_table.itemSelectionChanged.connect(self._on_selection_changed)
        section.addWidget(self._result_table)

        return section

    def _create_action_section(self) -> QVBoxLayout:
        section = QVBoxLayout()

        row = QHBoxLayout()
        row.setSpacing(8)

        self._connect_btn = QPushButton("连接")
        self._connect_btn.setEnabled(False)
        self._connect_btn.clicked.connect(self._on_connect)
        row.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("断开连接")
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        row.addWidget(self._disconnect_btn)

        row.addStretch()
        section.addLayout(row)
        return section

    def _create_executor_area(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._start_executor_button = QPushButton("开始执行")
        self._start_executor_button.setEnabled(False)
        self._start_executor_button.clicked.connect(self._on_start_executor_clicked)
        row.addWidget(self._start_executor_button)

        self._stop_executor_button = QPushButton("停止执行")
        self._stop_executor_button.setEnabled(False)
        self._stop_executor_button.clicked.connect(self._on_stop_executor_clicked)
        row.addWidget(self._stop_executor_button)

        row.addStretch()
        section.addLayout(row)

        self._executor_status_label = QLabel()
        section.addWidget(self._executor_status_label)

        self._executor_progress_bar = QProgressBar()
        self._executor_progress_bar.setRange(0, 100)
        self._executor_progress_bar.setValue(0)
        section.addWidget(self._executor_progress_bar)

        self._executor_step_label = QLabel("当前步骤：-")
        section.addWidget(self._executor_step_label)

        log_header = QHBoxLayout()
        log_title = QLabel("执行日志")
        log_header.addWidget(log_title)
        log_header.addStretch()
        self._clear_executor_log_button = QPushButton("清空日志")
        self._clear_executor_log_button.clicked.connect(self._clear_executor_logs)
        log_header.addWidget(self._clear_executor_log_button)
        section.addLayout(log_header)

        self._executor_log_text_edit = QPlainTextEdit()
        self._executor_log_text_edit.setReadOnly(True)
        self._executor_log_text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._executor_log_text_edit.setMinimumHeight(120)
        section.addWidget(self._executor_log_text_edit)

        return section

    def _create_status_section(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._indicator = QLabel()
        self._indicator.setObjectName("status_indicator")
        self._indicator.setFixedSize(16, 16)
        row.addWidget(self._indicator)

        self._status_text = QLabel()
        row.addWidget(self._status_text)

        row.addStretch()
        section.addLayout(row)

        self._execute_status_label = QLabel()
        section.addWidget(self._execute_status_label)

        self._window_info = QLabel()
        self._window_info.setVisible(False)
        section.addWidget(self._window_info)

        return section

    def _create_screenshot_area(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(8)

        title = QLabel("截图预览")
        section.addWidget(title)

        self._screenshot_preview_label = QLabel("暂无截图")
        self._screenshot_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._screenshot_preview_label.setProperty("class", "screenshot-placeholder")
        self._screenshot_preview_label.setMinimumHeight(120)
        section.addWidget(self._screenshot_preview_label)

        self._refresh_screenshot_button = QPushButton("刷新截图")
        self._refresh_screenshot_button.setEnabled(False)
        self._refresh_screenshot_button.clicked.connect(
            self._on_refresh_screenshot_clicked,
        )
        section.addWidget(self._refresh_screenshot_button)

        self._screenshot_status_label = QLabel()
        section.addWidget(self._screenshot_status_label)

        self._screenshot_meta_label = QLabel()
        self._screenshot_meta_label.setWordWrap(True)
        section.addWidget(self._screenshot_meta_label)

        return section

    def _on_search_text_changed(self, text: str) -> None:
        keyword = text.strip()
        if not keyword:
            self._search_debounce_timer.stop()
            self._handle_empty_keyword()
            return
        if self._connecting:
            return
        if self._is_executor_busy():
            self._show_executor_feedback(FeedbackCode.EXECUTOR_STOP_REQUIRED)
            return
        self._search_debounce_timer.start()

    def _trigger_debounced_search(self) -> None:
        keyword = self._search_input.text().strip()
        self._start_search(keyword)

    def _trigger_immediate_search(self) -> None:
        self._search_debounce_timer.stop()
        keyword = self._search_input.text().strip()
        self._start_search(keyword)

    def _handle_empty_keyword(self) -> None:
        self._invalidate_search()
        self._clear_search_results()
        self._set_search_state(SearchUiState.IDLE)

    def _start_search(self, keyword: str) -> None:
        keyword = keyword.strip()
        if not keyword:
            self._handle_empty_keyword()
            return
        if self._connecting:
            return
        if not self._ensure_can_change_connection():
            return

        self._search_request_id += 1
        request_id = self._search_request_id
        self._active_search_request_id = request_id
        self._search_running = True

        self._set_search_state(SearchUiState.SEARCHING)

        self._start_search_timeout(request_id)
        logger.info("触发异步窗口搜索, keyword=%s, request_id=%s", keyword, request_id)
        self._task_runner.start_search(request_id, keyword)

    def _on_search_finished(self, request_id: int, results: list) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            logger.debug(
                "Discard expired search result: request_id=%s, active=%s",
                request_id,
                self._active_search_request_id,
            )
            return

        self._search_running = False
        logger.debug(
            "窗口搜索完成, request_id=%s, 结果数量=%d",
            request_id,
            len(results),
        )

        if results:
            self._fill_search_results(results)
            self._set_search_state(SearchUiState.HAS_RESULT)
        else:
            self._clear_search_results()
            self._set_search_state(SearchUiState.EMPTY)

    def _on_search_failed(self, request_id: int, message: str) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            logger.debug(
                "Discard expired search failure: request_id=%s, active=%s",
                request_id,
                self._active_search_request_id,
            )
            return

        self._search_running = False
        logger.warning("Search worker failed: %s", message)
        self._clear_search_results()
        self._set_search_state(
            SearchUiState.ERROR,
            feedback_code=FeedbackCode.SEARCH_FAILED,
        )

    def _on_search_timeout(self, request_id: int) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            return

        self._invalidate_search()
        self._clear_search_results()
        logger.warning("Search timeout, request_id=%s", request_id)
        self._set_search_state(
            SearchUiState.ERROR,
            feedback_code=FeedbackCode.SEARCH_TIMEOUT,
        )

    def _clear_search_results(self) -> None:
        self._search_results = []
        self._result_table.setRowCount(0)

    def _fill_search_results(self, results: list[WindowInfo]) -> None:
        self._search_results = list(results)
        self._result_table.setRowCount(0)

        if not self._search_results:
            return

        self._search_results.sort(key=lambda w: w.match_score, reverse=True)

        for i, win in enumerate(self._search_results):
            self._result_table.insertRow(i)
            self._result_table.setItem(i, 0, QTableWidgetItem(win.title))
            self._result_table.setItem(i, 1, QTableWidgetItem(win.process_name))
            pid_item = QTableWidgetItem(str(win.pid))
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._result_table.setItem(i, 2, pid_item)
            status_text = "最小化" if win.is_minimized else "正常"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if win.is_minimized:
                status_item.setForeground(QColor("#f9e2af"))
            self._result_table.setItem(i, 3, status_item)

    def _on_selection_changed(self) -> None:
        selected = self._get_selected_window_info()
        if selected is not None and selected.is_minimized:
            self._show_hint_feedback(FeedbackCode.WINDOW_MINIMIZED)
        self._apply_ui_state()

    def _on_connect(self) -> None:
        if not self._ensure_can_change_connection():
            return

        window_info = self._get_selected_window_info()
        if window_info is None:
            logger.warning("点击连接按钮但无选中行")
            return

        if window_info.is_minimized:
            self._show_hint_feedback(FeedbackCode.WINDOW_MINIMIZED)
            self._apply_ui_state()
            return

        if self._is_connected_state():
            if not self._confirm_switch_connection(window_info):
                return
            self._disconnect_for_switch()

        self._start_connect(window_info)

    def _start_connect(self, window_info: WindowInfo) -> None:
        if self._connecting:
            return

        logger.info(
            "开始执行连接流程, title=%s, pid=%s",
            window_info.title,
            window_info.pid,
        )

        self._stop_health_timer()
        self._invalidate_health_checks()

        self._connect_request_id += 1
        request_id = self._connect_request_id
        self._active_connect_request_id = request_id

        self._connection_generation += 1
        generation = self._connection_generation
        self._connect_request_generations[request_id] = generation

        self._connecting = True
        self._pending_connect_window = window_info

        self._set_connection_state(ConnectionUiState.CONNECTING)

        self._start_connect_timeout(request_id)
        self._task_runner.start_connect(
            request_id,
            window_info,
            ConnectOptions(activate_on_connect=False),
        )
        logger.debug(
            "连接任务已提交, request_id=%s, generation=%s",
            request_id,
            generation,
        )

    def _on_connect_timeout(self, request_id: int) -> None:
        self._stop_connect_timeout(request_id)

        request_generation = self._connect_request_generations.pop(request_id, None)
        if not self._is_connect_result_current(request_id, request_generation):
            return

        logger.warning(
            "Connect timeout, request_id=%s, generation=%s",
            request_id,
            self._connection_generation,
        )
        self._active_connect_request_id = 0
        self._connection_generation += 1
        self._connecting = False
        self._pending_connect_window = None

        self._window_manager.disconnect_window()

        self._reset_capture_state()
        self._clear_screenshot_preview()
        self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_UNAVAILABLE)

        self._set_connection_state(
            ConnectionUiState.DISCONNECTED,
            get_feedback_text(FeedbackCode.CONNECT_TIMEOUT),
            feedback_level=FeedbackLevel.ERROR,
        )

    def _on_connect_finished(self, request_id: int, result: ConnectResult) -> None:
        self._stop_connect_timeout(request_id)

        request_generation = self._connect_request_generations.pop(request_id, None)
        if not self._is_connect_result_current(request_id, request_generation):
            if result.success:
                logger.warning(
                    "Discard expired connect result: request_id=%s, "
                    "request_generation=%s, current_generation=%s",
                    request_id,
                    request_generation,
                    self._connection_generation,
                )
                self._window_manager.disconnect_window()
            return

        self._connecting = False
        pending_window = self._pending_connect_window
        self._pending_connect_window = None

        logger.debug(
            "连接完成, request_id=%s, success=%s",
            request_id,
            result.success,
        )

        if result.success and result.window is not None:
            connected = result.window
            if pending_window is not None:
                self._current_window = pending_window
            elif self._current_window is None:
                self._current_window = WindowInfo(
                    hwnd=connected.hwnd,
                    title=connected.title,
                    process_name=connected.process_name,
                    pid=connected.pid,
                    width=connected.window_rect.width,
                    height=connected.window_rect.height,
                    match_score=1.0,
                )

            self._window_info.setText(
                f"窗口标题：{connected.title}  "
                f"PID：{connected.pid}  "
                f"客户区：{connected.client_size_text}"
            )
            self._set_connection_state(ConnectionUiState.CONNECTED_READY)
            self._health_timer.start()
        else:
            err_msg = result.error_message or get_feedback_text(
                FeedbackCode.CONNECT_FAILED,
            )
            logger.warning("Connect failed: %s", result)
            self._set_connection_state(
                ConnectionUiState.DISCONNECTED,
                err_msg,
                feedback_level=FeedbackLevel.ERROR,
            )
            if self._window_manager.is_connected():
                self._health_timer.start()

    def _on_connect_failed(self, request_id: int, message: str) -> None:
        self._stop_connect_timeout(request_id)

        request_generation = self._connect_request_generations.pop(request_id, None)
        if not self._is_connect_result_current(request_id, request_generation):
            return

        self._connecting = False
        self._pending_connect_window = None
        logger.warning("Connect worker failed: %s", message)
        self._set_connection_state(
            ConnectionUiState.DISCONNECTED,
            get_feedback_text(FeedbackCode.CONNECT_EXCEPTION),
            feedback_level=FeedbackLevel.ERROR,
        )

        if self._window_manager.is_connected():
            self._health_timer.start()

    def _on_disconnect(self) -> None:
        if not self._ensure_can_change_connection():
            return
        logger.info("用户点击断开连接按钮")
        self._do_disconnect()

    def _do_disconnect(self) -> None:
        logger.info("开始执行断开连接流程")

        self._stop_health_timer()

        self._connection_generation += 1
        self._active_connect_request_id = 0
        self._active_health_request_id = 0
        self._connecting = False
        self._health_check_running = False
        self._connect_request_generations.clear()
        self._health_request_generations.clear()
        self._clear_connect_timeouts()
        self._clear_health_timeouts()

        self._reset_capture_state()
        self._clear_screenshot_preview()
        self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_UNAVAILABLE)

        self._window_manager.disconnect_window()

        self._current_window = None
        self._pending_connect_window = None
        self._window_info.clear()
        self._set_connection_state(
            ConnectionUiState.DISCONNECTED,
            get_feedback_text(FeedbackCode.DISCONNECT_SUCCESS),
            feedback_level=FeedbackLevel.INFO,
        )

        logger.info("断开连接完成")

    def _stop_health_timer(self) -> None:
        self._health_timer.stop()
        logger.debug("健康检测定时器已停止")

    def _on_health_check(self) -> None:
        if self._health_check_running or self._connecting:
            return

        self._health_request_id += 1
        request_id = self._health_request_id
        self._active_health_request_id = request_id
        self._health_request_generations[request_id] = self._connection_generation
        self._health_check_running = True

        self._start_health_timeout(request_id)
        logger.debug(
            "提交健康检测任务, request_id=%s, generation=%s",
            request_id,
            self._connection_generation,
        )
        self._task_runner.start_health_check(request_id)

    def _on_health_finished(self, request_id: int, health_result: HealthCheckResult) -> None:
        self._stop_health_timeout(request_id)

        request_generation = self._health_request_generations.pop(request_id, None)

        if request_id == self._active_health_request_id:
            self._health_check_running = False

        if not self._is_health_result_current(request_id, request_generation):
            logger.debug(
                "Discard expired health result: request_id=%s, "
                "request_generation=%s, current_generation=%s",
                request_id,
                request_generation,
                self._connection_generation,
            )
            return

        logger.debug(
            "健康检测完成, request_id=%s, status=%s, ready=%s",
            request_id,
            health_result.status.value,
            health_result.is_ready,
        )

        if health_result.status == HealthStatus.NOT_CONNECTED:
            if not self._window_manager.is_connected():
                self._stop_health_timer()
                self._current_window = None
                self._window_info.clear()
                self._reset_capture_state()
                self._clear_screenshot_preview()
                self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_UNAVAILABLE)
                self._set_connection_state(ConnectionUiState.DISCONNECTED)
            return

        if health_result.window is not None:
            connected = health_result.window
            self._window_info.setText(
                f"窗口标题：{connected.title}  "
                f"PID：{connected.pid}  "
                f"客户区：{connected.client_size_text}"
            )

        self._apply_health_result(health_result)

    def _on_health_failed(self, request_id: int, message: str) -> None:
        self._stop_health_timeout(request_id)

        request_generation = self._health_request_generations.pop(request_id, None)

        if request_id == self._active_health_request_id:
            self._health_check_running = False

        if not self._is_health_result_current(request_id, request_generation):
            return

        logger.warning("Health worker failed: %s", message)
        self._set_connection_state(
            ConnectionUiState.CONNECTED_UNHEALTHY,
            get_feedback_text(FeedbackCode.HEALTH_EXCEPTION),
            feedback_level=FeedbackLevel.WARNING,
        )

    def _on_health_timeout(self, request_id: int) -> None:
        self._stop_health_timeout(request_id)

        request_generation = self._health_request_generations.pop(request_id, None)
        if not self._is_health_result_current(request_id, request_generation):
            return

        self._active_health_request_id = 0
        self._health_check_running = False
        logger.warning("Health check timeout, request_id=%s", request_id)
        self._set_connection_state(
            ConnectionUiState.CONNECTED_UNHEALTHY,
            get_feedback_text(FeedbackCode.HEALTH_TIMEOUT),
            feedback_level=FeedbackLevel.WARNING,
        )

    def _next_capture_request_id(self) -> int:
        self._capture_request_id += 1
        return self._capture_request_id

    def _is_active_capture_result(self, request_id: int) -> bool:
        if request_id != self._active_capture_request_id:
            logger.debug(
                "Discard expired screenshot result: request_id=%s, active=%s",
                request_id,
                self._active_capture_request_id,
            )
            return False

        request_generation = self._capture_request_generations.get(request_id)
        if request_generation != self._connection_generation:
            logger.debug(
                "Discard screenshot result due to generation mismatch: "
                "request_id=%s, request_generation=%s, current_generation=%s",
                request_id,
                request_generation,
                self._connection_generation,
            )
            return False

        return True

    def _update_screenshot_button_state(self) -> None:
        context = self._window_manager.get_connected_context()
        enabled = (
            context is not None
            and self._is_connected_state()
            and not self._connecting
            and not self._is_capturing
            and not self._is_executor_busy()
        )
        self._refresh_screenshot_button.setEnabled(enabled)

    def _show_screenshot_feedback(
        self,
        code: FeedbackCode,
        **kwargs: object,
    ) -> None:
        text = get_feedback_text(code, **kwargs)
        level = get_feedback_level(code)
        self._screenshot_status_label.setText(text)
        self._apply_feedback_style(self._screenshot_status_label, level)

    def _show_screenshot_message(
        self,
        message: str,
        level: FeedbackLevel = FeedbackLevel.ERROR,
    ) -> None:
        self._screenshot_status_label.setText(message)
        self._apply_feedback_style(self._screenshot_status_label, level)

    def _clear_screenshot_preview(self) -> None:
        self._last_screenshot_pixmap = None
        self._screenshot_preview_label.clear()
        self._screenshot_preview_label.setText("暂无截图")
        self._screenshot_meta_label.clear()

    def _on_refresh_screenshot_clicked(self) -> None:
        if self._is_capturing:
            return

        context = self._window_manager.get_connected_context()
        if context is None:
            self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_UNAVAILABLE)
            return

        request_id = self._next_capture_request_id()
        self._active_capture_request_id = request_id
        self._capture_request_generations[request_id] = self._connection_generation

        self._is_capturing = True
        self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_CAPTURING)
        self._update_screenshot_button_state()
        self._refresh_executor_ready_state()

        self._capture_timeout_timer.start(SCREENSHOT_TIMEOUT_MS)

        options = CaptureOptions(
            region=CaptureRegion.CLIENT,
            backend=CaptureBackendType.AUTO,
            require_foreground=False,
            allow_occluded=True,
        )

        logger.debug(
            "Start screenshot capture: request_id=%s, generation=%s",
            request_id,
            self._connection_generation,
        )
        self._screenshot_task_runner.start_capture(
            request_id=request_id,
            context=context,
            options=options,
        )

    def _on_capture_finished(
        self,
        request_id: int,
        result: ScreenshotResult,
    ) -> None:
        if not self._is_active_capture_result(request_id):
            return

        self._capture_timeout_timer.stop()
        self._capture_request_generations.pop(request_id, None)
        self._active_capture_request_id = 0
        self._is_capturing = False

        if result.success and result.image is not None:
            logger.debug("Screenshot capture success: request_id=%s", request_id)
            self._update_screenshot_preview(result)
            self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_SUCCESS)
            self._show_screenshot_meta(result)
        else:
            logger.warning(
                "Screenshot capture failed: request_id=%s, message=%s",
                request_id,
                result.message,
            )
            self._show_screenshot_failed_result(result)

        self._update_screenshot_button_state()
        self._refresh_executor_ready_state()

    def _on_capture_failed(self, request_id: int, message: str) -> None:
        if not self._is_active_capture_result(request_id):
            return

        self._capture_timeout_timer.stop()
        self._capture_request_generations.pop(request_id, None)
        self._active_capture_request_id = 0
        self._is_capturing = False

        logger.warning("Screenshot worker failed: %s", message)
        self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_FAILED)
        self._update_screenshot_button_state()
        self._refresh_executor_ready_state()

    def _on_capture_timeout(self) -> None:
        request_id = self._active_capture_request_id
        if request_id == 0:
            return

        logger.warning("Screenshot timeout: request_id=%s", request_id)
        self._active_capture_request_id = 0
        self._is_capturing = False
        self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_TIMEOUT)
        self._update_screenshot_button_state()
        self._refresh_executor_ready_state()

    def _show_screenshot_failed_result(self, result: ScreenshotResult) -> None:
        if result.message:
            self._show_screenshot_message(result.message)
            self._screenshot_meta_label.setText(result.message)
        else:
            self._show_screenshot_feedback(FeedbackCode.SCREENSHOT_FAILED)

    def _show_screenshot_meta(self, result: ScreenshotResult) -> None:
        captured_time = (
            result.captured_at.strftime("%H:%M:%S")
            if result.captured_at
            else "-"
        )
        occluded_text = "是" if result.supports_occluded else "否"
        meta = (
            f"尺寸：{result.width} x {result.height} | "
            f"后端：{result.backend.value} | "
            f"时间：{captured_time} | "
            f"遮挡支持：{occluded_text}"
        )
        if result.message:
            meta += f" | 提示：{result.message}"
        self._screenshot_meta_label.setText(meta)

    def _update_screenshot_preview(self, result: ScreenshotResult) -> None:
        if result.image is None:
            return
        pixmap = self._pil_image_to_pixmap(result.image)
        self._set_screenshot_pixmap(pixmap)

    def _pil_image_to_pixmap(self, image: Image.Image) -> QPixmap:
        rgba_image = image.convert("RGBA")
        data = rgba_image.tobytes("raw", "RGBA")
        qimage = QImage(
            data,
            rgba_image.width,
            rgba_image.height,
            QImage.Format.Format_RGBA8888,
        )
        return QPixmap.fromImage(qimage.copy())

    def _set_screenshot_pixmap(self, pixmap: QPixmap) -> None:
        self._last_screenshot_pixmap = pixmap
        scaled = pixmap.scaled(
            self._screenshot_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._screenshot_preview_label.setPixmap(scaled)
