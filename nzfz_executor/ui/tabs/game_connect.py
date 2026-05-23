"""游戏连接页签：提供窗口搜索、连接、断连及健康检测的可视化交互界面。"""

from __future__ import annotations

import logging
from enum import Enum

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCloseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)

from nzfz_executor.core.window_manager import WindowManager
from nzfz_executor.core.models import (
    WindowInfo,
    HealthStatus,
    ConnectResult,
    HealthCheckResult,
    ConnectOptions,
)
from nzfz_executor.ui.workers import WindowTaskRunner

logger = logging.getLogger(__name__)

SEARCH_DEBOUNCE_MS = 300
SEARCH_TIMEOUT_MS = 3000
CONNECT_TIMEOUT_MS = 5000
HEALTH_TIMEOUT_MS = 2000


class ConnectState(str, Enum):
    """连接状态枚举，描述当前与游戏窗口的连接状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ABNORMAL = "abnormal"
    TIMEOUT = "timeout"


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

        self._state: ConnectState = ConnectState.DISCONNECTED
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

        self._status_label: QLabel
        self._search_input: QLineEdit
        self._search_btn: QPushButton
        self._result_table: QTableWidget
        self._connect_btn: QPushButton
        self._disconnect_btn: QPushButton
        self._indicator: QLabel
        self._status_text: QLabel
        self._window_info: QLabel

        self._init_ui()
        self._update_button_states()
        self._set_status(ConnectState.DISCONNECTED)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self) -> None:
        """页面销毁时停止定时器并使在途请求失效。"""
        self._search_debounce_timer.stop()
        self._stop_health_timer()
        self._invalidate_search()
        self._active_connect_request_id = 0
        self._active_health_request_id = 0
        self._connection_generation += 1
        self._clear_search_timeouts()
        self._clear_connect_timeouts()
        self._clear_health_timeouts()

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
        layout.addLayout(self._create_screenshot_placeholder())
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

        self._window_info = QLabel()
        self._window_info.setVisible(False)
        section.addWidget(self._window_info)

        return section

    def _create_screenshot_placeholder(self) -> QVBoxLayout:
        section = QVBoxLayout()

        placeholder = QLabel("截图功能暂未实现")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setProperty("class", "screenshot-placeholder")
        placeholder.setMinimumHeight(120)
        section.addWidget(placeholder)

        return section

    def _on_search_text_changed(self, text: str) -> None:
        keyword = text.strip()
        if not keyword:
            self._search_debounce_timer.stop()
            self._handle_empty_keyword()
            return
        if self._connecting:
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
        self._show_tip("请输入窗口标题、进程名或 PID")
        self._update_button_states()

    def _start_search(self, keyword: str) -> None:
        keyword = keyword.strip()
        if not keyword:
            self._handle_empty_keyword()
            return
        if self._connecting:
            return

        self._search_request_id += 1
        request_id = self._search_request_id
        self._active_search_request_id = request_id
        self._search_running = True
        self._update_button_states()

        self._start_search_timeout(request_id)
        logger.info("触发异步窗口搜索, keyword=%s, request_id=%s", keyword, request_id)
        self._task_runner.start_search(request_id, keyword)

    def _on_search_finished(self, request_id: int, results: list) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            logger.debug("忽略过期搜索结果, request_id=%s", request_id)
            return

        self._search_running = False
        logger.info(
            "窗口搜索完成, request_id=%s, 结果数量=%d",
            request_id,
            len(results),
        )
        self._fill_search_results(results)
        self._update_button_states()

    def _on_search_failed(self, request_id: int, message: str) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            logger.debug("忽略过期搜索失败, request_id=%s", request_id)
            return

        self._search_running = False
        logger.error("窗口搜索异常, request_id=%s, error=%s", request_id, message)
        self._show_tip(f"搜索失败：{message}")
        self._update_button_states()

    def _on_search_timeout(self, request_id: int) -> None:
        self._stop_search_timeout(request_id)

        if request_id != self._active_search_request_id:
            return

        self._invalidate_search()
        self._show_tip("搜索窗口超时，请稍后重试")
        self._update_button_states()

    def _clear_search_results(self) -> None:
        self._search_results = []
        self._result_table.setRowCount(0)

    def _fill_search_results(self, results: list[WindowInfo]) -> None:
        self._search_results = list(results)
        self._result_table.setRowCount(0)

        if not self._search_results:
            self._result_table.setRowCount(1)
            self._result_table.setSpan(0, 0, 1, 4)
            empty_item = QTableWidgetItem("无匹配结果")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._result_table.setItem(0, 0, empty_item)
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
        self._update_button_states()

    def _on_connect(self) -> None:
        if self._connecting or self._search_running:
            return

        selected_rows = self._result_table.selectionModel().selectedRows()
        if not selected_rows:
            logger.warning("点击连接按钮但无选中行")
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self._search_results):
            return

        window_info = self._search_results[row]
        if window_info.is_minimized:
            self._show_tip("⚠ 窗口已最小化，请恢复窗口后重试")
            return

        if self._state in (ConnectState.CONNECTED, ConnectState.ABNORMAL):
            reply = QMessageBox.question(
                self,
                "确认切换连接",
                f"当前已连接「{self._current_window.title}」，"
                f"确认后将断开并连接新窗口，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return
            self._do_disconnect()

        self._do_connect(window_info)

    def _do_connect(self, window_info: WindowInfo) -> None:
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

        self._set_status(ConnectState.CONNECTING)
        self._update_button_states()

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

        logger.warning("连接超时, request_id=%s", request_id)
        self._active_connect_request_id = 0
        self._connection_generation += 1
        self._connecting = False
        self._pending_connect_window = None

        self._window_manager.disconnect_window()

        self._set_status(ConnectState.TIMEOUT)
        self._show_tip("连接窗口超时，请稍后重试")
        self._update_button_states()

    def _on_connect_finished(self, request_id: int, result: ConnectResult) -> None:
        self._stop_connect_timeout(request_id)

        request_generation = self._connect_request_generations.pop(request_id, None)
        if not self._is_connect_result_current(request_id, request_generation):
            if result.success:
                logger.warning(
                    "丢弃过期连接成功结果并兜底断开, request_id=%s",
                    request_id,
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

            self._set_status(ConnectState.CONNECTED)
            self._window_info.setText(
                f"窗口标题：{connected.title}  "
                f"PID：{connected.pid}  "
                f"客户区：{connected.client_size_text}"
            )
            self._window_info.setVisible(True)
            self._health_timer.start()
        else:
            self._set_status(ConnectState.DISCONNECTED)
            err_msg = (
                f"连接失败：{result.error_message}"
                if result.error_message
                else "连接失败"
            )
            self._show_tip(err_msg)
            if self._window_manager.is_connected():
                self._health_timer.start()

    def _on_connect_failed(self, request_id: int, message: str) -> None:
        self._stop_connect_timeout(request_id)

        request_generation = self._connect_request_generations.pop(request_id, None)
        if not self._is_connect_result_current(request_id, request_generation):
            return

        self._connecting = False
        self._pending_connect_window = None
        logger.error("连接任务异常, request_id=%s, error=%s", request_id, message)
        self._set_status(ConnectState.DISCONNECTED)
        self._show_tip(f"连接失败：{message}")

        if self._window_manager.is_connected():
            self._health_timer.start()

    def _on_disconnect(self) -> None:
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

        self._window_manager.disconnect_window()

        self._current_window = None
        self._pending_connect_window = None
        self._set_status(ConnectState.DISCONNECTED)
        self._window_info.clear()
        self._window_info.setVisible(False)

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
            logger.debug("忽略过期健康检测结果, request_id=%s", request_id)
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
                self._set_status(ConnectState.DISCONNECTED)
                self._window_info.clear()
                self._window_info.setVisible(False)
            return

        if health_result.window is not None:
            connected = health_result.window
            self._window_info.setText(
                f"窗口标题：{connected.title}  "
                f"PID：{connected.pid}  "
                f"客户区：{connected.client_size_text}"
            )
            self._window_info.setVisible(True)

        if health_result.is_ready:
            if self._state == ConnectState.ABNORMAL:
                logger.info("连接从异常恢复, 切回已连接状态")
            self._set_status(ConnectState.CONNECTED)
            self._status_text.setText("已连接，执行就绪")
        elif health_result.is_healthy:
            if self._state == ConnectState.ABNORMAL:
                logger.info("连接从异常恢复, 切回已连接状态")
            self._set_status(ConnectState.CONNECTED)
            self._status_text.setText(health_result.message)
        elif health_result.status == HealthStatus.ERROR:
            self._status_text.setText(f"检测异常：{health_result.message}")
            self._set_status(ConnectState.ABNORMAL)
        else:
            self._status_text.setText(f"连接异常：{health_result.message}")
            self._set_status(ConnectState.ABNORMAL)

    def _on_health_failed(self, request_id: int, message: str) -> None:
        self._stop_health_timeout(request_id)

        request_generation = self._health_request_generations.pop(request_id, None)

        if request_id == self._active_health_request_id:
            self._health_check_running = False

        if not self._is_health_result_current(request_id, request_generation):
            return

        logger.error("健康检测任务异常, request_id=%s, error=%s", request_id, message)
        self._status_text.setText(f"检测异常：{message}")
        self._set_status(ConnectState.ABNORMAL)

    def _on_health_timeout(self, request_id: int) -> None:
        self._stop_health_timeout(request_id)

        request_generation = self._health_request_generations.pop(request_id, None)
        if not self._is_health_result_current(request_id, request_generation):
            return

        self._active_health_request_id = 0
        self._health_check_running = False
        self._status_text.setText("窗口状态检测超时")
        self._set_status(ConnectState.ABNORMAL)
        logger.warning("健康检测超时, request_id=%s", request_id)

    def _set_status(self, state: ConnectState) -> None:
        old_state = self._state
        self._state = state
        logger.info("连接状态变更: %s → %s", old_state.value, state.value)

        color_map = {
            ConnectState.DISCONNECTED: "#f38ba8",
            ConnectState.CONNECTING: "#f9e2af",
            ConnectState.CONNECTED: "#a6e3a1",
            ConnectState.ABNORMAL: "#f9e2af",
            ConnectState.TIMEOUT: "#f38ba8",
        }

        text_map = {
            ConnectState.DISCONNECTED: "未连接",
            ConnectState.CONNECTING: "连接中…",
            ConnectState.CONNECTED: "已连接",
            ConnectState.TIMEOUT: "连接超时，请重试",
        }

        color = color_map.get(state, "#f38ba8")
        self._indicator.setStyleSheet(
            f"QLabel#status_indicator {{"
            f"  background-color: {color};"
            f"  border-radius: 8px;"
            f"  min-width: 16px;"
            f"  min-height: 16px;"
            f"}}"
        )

        if state != ConnectState.ABNORMAL:
            self._status_text.setText(text_map.get(state, "未连接"))

        if state == ConnectState.CONNECTED:
            self._window_info.setVisible(True)
        elif state != ConnectState.ABNORMAL:
            self._window_info.setVisible(False)

        self._update_button_states()

    def _update_button_states(self) -> None:
        self._search_btn.setEnabled(not self._connecting)

        has_selection = bool(self._result_table.selectedIndexes())
        can_connect = has_selection and not self._search_running and not self._connecting
        if has_selection and can_connect:
            selected_rows = self._result_table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                if 0 <= row < len(self._search_results):
                    can_connect = not self._search_results[row].is_minimized

        self._connect_btn.setEnabled(can_connect)
        self._disconnect_btn.setEnabled(
            self._state in (ConnectState.CONNECTED, ConnectState.ABNORMAL)
        )

    def _show_tip(self, message: str) -> None:
        logger.warning("UI 提示: %s", message)
        self._status_label.setText(message)
        self._status_label.setVisible(True)
