"""游戏连接页签：提供窗口搜索、连接、断连及健康检测的可视化交互界面。"""

from __future__ import annotations

import logging
from enum import Enum

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy,
)

from nzfz_executor.core.window_manager import (
    WindowInfo, HealthStatus,
    search_windows, connect_window, disconnect_window, check_health,
)

logger = logging.getLogger(__name__)


class ConnectState(str, Enum):
    """连接状态枚举，描述当前与游戏窗口的连接状态。"""

    DISCONNECTED = "disconnected"
    """未连接：尚未与任何游戏窗口建立连接"""
    CONNECTING = "connecting"
    """连接中：正在尝试与目标窗口建立连接"""
    CONNECTED = "connected"
    """已连接：已成功与游戏窗口建立连接"""
    ABNORMAL = "abnormal"
    """连接异常：已建立的连接出现异常（如句柄失效、进程退出等）"""
    TIMEOUT = "timeout"
    """连接超时：连接操作在规定时间内未完成"""


class ConnectWorker(QThread):
    """连接工作线程，在后台执行窗口连接操作，避免阻塞 UI 主线程。

    信号:
        finished: 连接完成信号，携带 (成功标志, 错误信息)
    """

    finished = Signal(bool, str)
    """连接完成信号
    Args:
        success (bool): 连接是否成功
        error (str): 错误信息，成功时为空字符串
    """

    def __init__(self, window: WindowInfo) -> None:
        """初始化连接工作线程。

        Args:
            window: 目标窗口的信息数据对象
        """
        super().__init__()
        self._window = window
        """目标窗口信息"""

    def run(self) -> None:
        """在线程中执行连接操作。

        调用 connect_window 尝试连接目标窗口，
        成功时发射 finished(True, "")，异常时发射 finished(False, str(e))。
        """
        logger.info("后台线程开始连接窗口, title=%s, pid=%s", self._window.title, self._window.pid)
        try:
            connect_window(self._window)
            self.finished.emit(True, "")
            logger.info("后台线程连接窗口成功")
        except Exception as e:
            logger.error("后台线程连接窗口异常: %s", e)
            self.finished.emit(False, str(e))


class GameConnectTab(QWidget):
    """游戏连接页签，提供窗口搜索、连接管理及健康监测的完整 UI。

    包含搜索区、操作区、状态区和截图占位区四个功能区块。
    """

    def __init__(self) -> None:
        """初始化游戏连接页签，构建全部 UI 区块并设置初始状态。"""
        super().__init__()

        self._state: ConnectState = ConnectState.DISCONNECTED
        """当前连接状态"""

        self._current_window: WindowInfo | None = None
        """当前已连接的窗口信息，未连接时为 None"""

        self._search_results: list[WindowInfo] = []
        """最近一次搜索结果的缓存列表"""

        self._health_timer: QTimer = QTimer(self)
        """健康检测定时器，连接成功后每秒触发一次"""

        self._timeout_timer: QTimer = QTimer(self)
        """连接超时定时器，单次触发，超时时间为 5 秒"""

        self._worker: ConnectWorker | None = None
        """当前正在运行的连接工作线程，未运行时为 None"""

        self._status_label: QLabel
        """页签顶部状态提示栏，用于显示警告或操作反馈"""

        self._search_input: QLineEdit
        """搜索关键词输入框"""

        self._search_btn: QPushButton
        """搜索按钮"""

        self._result_table: QTableWidget
        """搜索结果表格，展示窗口标题、进程名、PID"""

        self._connect_btn: QPushButton
        """连接按钮"""

        self._disconnect_btn: QPushButton
        """断开连接按钮"""

        self._indicator: QLabel
        """状态指示灯，以圆点颜色表示当前连接状态"""

        self._status_text: QLabel
        """状态文字，描述当前连接状态的详细文本"""

        self._window_info: QLabel
        """窗口信息栏，显示当前连接窗口的详细信息"""

        self._init_ui()
        self._update_button_states()
        self._set_status(ConnectState.DISCONNECTED)

    # ------------------------------------------------------------------
    #  UI 构建方法
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        """构建页签主布局，依次创建搜索区、操作区、状态区和截图占位区。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addLayout(self._create_search_section())
        layout.addLayout(self._create_action_section())
        layout.addLayout(self._create_status_section())
        layout.addLayout(self._create_screenshot_placeholder())
        layout.addStretch()

    def _create_search_section(self) -> QVBoxLayout:
        """创建搜索区布局。

        包含关键词输入框 + 搜索按钮，以及展示搜索结果的表格。

        Returns:
            QVBoxLayout: 搜索区布局
        """
        section = QVBoxLayout()
        section.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入进程名或窗口标题")
        search_row.addWidget(self._search_input)

        self._search_btn = QPushButton("搜索")
        self._search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_btn)

        section.addLayout(search_row)

        self._result_table = QTableWidget(0, 3)
        self._result_table.setHorizontalHeaderLabels(["窗口标题", "进程名", "PID"])
        self._result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._result_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._result_table.horizontalHeader().setStretchLastSection(True)
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._result_table.itemSelectionChanged.connect(self._on_selection_changed)
        section.addWidget(self._result_table)

        return section

    def _create_action_section(self) -> QVBoxLayout:
        """创建连接操作区布局。

        包含连接按钮和断开连接按钮。

        Returns:
            QVBoxLayout: 操作区布局
        """
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
        """创建状态区布局。

        包含状态指示灯、状态文字和窗口信息栏。

        Returns:
            QVBoxLayout: 状态区布局
        """
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
        """创建截图占位区布局。

        使用 QSS 中 .screenshot-placeholder 样式渲染占位区域。

        Returns:
            QVBoxLayout: 截图占位区布局
        """
        section = QVBoxLayout()

        placeholder = QLabel("截图功能暂未实现")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setProperty("class", "screenshot-placeholder")
        placeholder.setMinimumHeight(120)
        section.addWidget(placeholder)

        return section

    # ------------------------------------------------------------------
    #  事件处理方法
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        """搜索按钮点击处理。

        根据输入关键词调用 search_windows 获取匹配窗口列表，
        清空并重新填充结果表格。无结果时显示占位提示行。
        """
        keyword = self._search_input.text().strip()
        if not keyword:
            self._show_tip("⚠ 请输入关键词")
            return

        logger.info("触发窗口搜索, keyword=%s", keyword)
        self._search_results = search_windows(keyword)
        logger.info("窗口搜索完成, keyword=%s, 结果数量=%d", keyword, len(self._search_results))

        self._result_table.setRowCount(0)

        if not self._search_results:
            self._result_table.setRowCount(1)
            self._result_table.setSpan(0, 0, 1, 3)
            empty_item = QTableWidgetItem("无匹配结果")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._result_table.setItem(0, 0, empty_item)
            logger.debug("搜索结果为空, keyword=%s", keyword)
            return

        self._search_results.sort(key=lambda w: w.match_score, reverse=True)

        for i, win in enumerate(self._search_results):
            self._result_table.insertRow(i)
            self._result_table.setItem(i, 0, QTableWidgetItem(win.title))
            self._result_table.setItem(i, 1, QTableWidgetItem(win.process_name))
            pid_item = QTableWidgetItem(str(win.pid))
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._result_table.setItem(i, 2, pid_item)

    def _on_selection_changed(self) -> None:
        """表格选中行变化处理。

        当存在选中行时启用连接按钮，否则禁用。
        """
        selected = self._result_table.selectedIndexes()
        if selected:
            self._connect_btn.setEnabled(True)
            logger.debug("表格选中行变化, 当前有选中行")
        else:
            self._connect_btn.setEnabled(False)
            logger.debug("表格选中行变化, 当前无选中行")

    def _on_connect(self) -> None:
        """连接按钮点击处理。

        获取当前选中行对应的窗口信息，若已处于连接状态则弹出确认对话框，
        用户确认后再执行切换连接。
        """
        selected_rows = self._result_table.selectionModel().selectedRows()
        if not selected_rows:
            logger.warning("点击连接按钮但无选中行")
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self._search_results):
            logger.warning("选中行索引越界, row=%d, results=%d", row, len(self._search_results))
            return

        window_info = self._search_results[row]
        logger.info("发起连接请求, title=%s, pid=%s, 当前状态=%s",
                     window_info.title, window_info.pid, self._state.value)

        if self._state in (ConnectState.CONNECTED, ConnectState.ABNORMAL):
            reply = QMessageBox.question(
                self,
                "确认切换连接",
                f"当前已连接「{self._current_window.title}」，"
                f"确认后将断开并连接新窗口，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                logger.info("用户取消切换连接")
                return
            logger.info("用户确认切换连接，先断开当前连接")
            self._do_disconnect()

        self._do_connect(window_info)

    def _do_connect(self, window_info: WindowInfo) -> None:
        """实际执行连接流程。

        设置连接中状态，禁用操作按钮，启动超时计时器，
        创建并启动后台连接工作线程。

        Args:
            window_info: 目标窗口信息
        """
        logger.info("开始执行连接流程, title=%s, pid=%s", window_info.title, window_info.pid)

        self._set_status(ConnectState.CONNECTING)
        self._connect_btn.setEnabled(False)
        self._disconnect_btn.setEnabled(False)

        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(5000)
        try:
            self._timeout_timer.timeout.disconnect(self._on_connect_timeout)
        except (TypeError, RuntimeError):
            pass
        self._timeout_timer.timeout.connect(self._on_connect_timeout)
        self._timeout_timer.start()
        logger.debug("连接超时计时器已启动, timeout=5s")

        self._worker = ConnectWorker(window_info)
        self._worker.finished.connect(self._on_connect_finished)
        self._worker.start()
        logger.debug("连接工作线程已启动")

    def _on_connect_timeout(self) -> None:
        """连接超时回调。

        停止后台工作线程，将状态切换为 TIMEOUT。
        """
        logger.warning("连接超时, 强制终止工作线程")

        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()
            logger.debug("工作线程已强制终止")

        self._set_status(ConnectState.TIMEOUT)

    def _on_connect_finished(self, success: bool, error: str) -> None:
        """连接完成回调，由后台工作线程触发。

        Args:
            success: 连接是否成功
            error: 错误信息，成功时为空字符串
        """
        self._timeout_timer.stop()
        logger.debug("连接完成回调触发, success=%s, error=%s", success, error)

        if success:
            self._current_window = self._worker._window  # type: ignore[union-attr]
            self._set_status(ConnectState.CONNECTED)

            self._window_info.setText(
                f"窗口标题：{self._current_window.title}  "
                f"PID：{self._current_window.pid}  "
                f"分辨率：{self._current_window.width}×{self._current_window.height}"
            )
            self._window_info.setVisible(True)

            self._health_timer.setInterval(1000)
            try:
                self._health_timer.timeout.disconnect(self._on_health_check)
            except (TypeError, RuntimeError):
                pass
            self._health_timer.timeout.connect(self._on_health_check)
            self._health_timer.start()
            logger.info("连接成功，健康检测定时器已启动, interval=1s")
        else:
            self._set_status(ConnectState.DISCONNECTED)
            err_msg = f"连接失败：{error}" if error else "连接失败"
            self._show_tip(err_msg)
            logger.error("连接失败, error=%s", error)

        self._worker = None

    def _on_disconnect(self) -> None:
        """断开连接按钮点击处理。"""
        logger.info("用户点击断开连接按钮")
        self._do_disconnect()

    def _do_disconnect(self) -> None:
        """实际执行断开连接流程。

        停止健康检测定时器，释放窗口连接，恢复 UI 状态。
        """
        logger.info("开始执行断开连接流程")

        self._health_timer.stop()
        logger.debug("健康检测定时器已停止")

        disconnect_window()

        self._current_window = None
        self._set_status(ConnectState.DISCONNECTED)

        self._window_info.clear()
        self._window_info.setVisible(False)

        logger.info("断开连接完成")

    def _on_health_check(self) -> None:
        """健康检测回调，每秒触发一次。

        检测当前窗口连接的健康状态：
        - 健康且非 ABNORMAL → 保持 CONNECTED
        - 从 ABNORMAL 恢复 → 切回 CONNECTED
        - 健康状态异常 → 切为 ABNORMAL 并尝试重连
        """
        status = check_health()
        logger.debug("健康检测, status=%s", status.value)

        if status == HealthStatus.HEALTHY:
            if self._state == ConnectState.ABNORMAL:
                logger.info("连接从异常恢复, 切回已连接状态")
                self._set_status(ConnectState.CONNECTED)
        else:
            if self._current_window is not None:
                self._status_text.setText(f"连接异常：{status.value}")
                self._set_status(ConnectState.ABNORMAL)
                logger.warning("连接异常, status=%s, 尝试重连", status.value)

                try:
                    connect_window(self._current_window)
                    logger.info("重连成功")
                    self._set_status(ConnectState.CONNECTED)
                except Exception as e:
                    logger.error("重连失败: %s, 维持异常状态等待下一轮检测", e)

    # ------------------------------------------------------------------
    #  状态管理方法
    # ------------------------------------------------------------------

    def _set_status(self, state: ConnectState) -> None:
        """统一状态切换方法。

        更新内部状态、指示灯颜色、状态文字，
        并根据状态控制窗口信息栏的显示与隐藏。

        Args:
            state: 目标连接状态
        """
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

        if state == ConnectState.ABNORMAL:
            pass
        else:
            self._status_text.setText(text_map.get(state, "未连接"))

        if state == ConnectState.CONNECTED:
            self._window_info.setVisible(True)
        else:
            self._window_info.setVisible(False)

        self._update_button_states()

    def _update_button_states(self) -> None:
        """按钮状态联动更新。

        连接按钮：仅在有选中行时启用
        断开按钮：仅在已连接或连接异常时启用
        """
        has_selection = bool(self._result_table.selectedIndexes())
        self._connect_btn.setEnabled(has_selection)

        self._disconnect_btn.setEnabled(
            self._state in (ConnectState.CONNECTED, ConnectState.ABNORMAL)
        )

        logger.debug(
            "按钮状态更新, connect_enabled=%s, disconnect_enabled=%s",
            has_selection,
            self._state in (ConnectState.CONNECTED, ConnectState.ABNORMAL),
        )

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------

    def _show_tip(self, message: str) -> None:
        """在页签顶部状态栏显示提示信息。

        Args:
            message: 提示信息文本
        """
        logging.warning(message)
        logger.warning("UI 提示: %s", message)