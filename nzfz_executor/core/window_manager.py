"""窗口管理器：执行器窗口连接核心管理类。

提供窗口搜索、连接、断开、健康检测的统一接口，屏蔽 Windows API 细节。
"""

from __future__ import annotations

import logging
import platform
from typing import Optional

from nzfz_executor.core.models import (
    WindowInfo,
    ConnectedWindow,
    ConnectOptions,
    ConnectResult,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import psutil
        import win32gui
        import win32process
    except ImportError:
        psutil = None
        win32gui = None
        win32process = None
else:
    psutil = None
    win32gui = None
    win32process = None


class WindowManager:
    """
    Windows 游戏窗口连接管理器。

    职责：
    - 搜索真实 Windows 顶层窗口
    - 连接并绑定指定窗口
    - 保存当前连接窗口上下文
    - 断开连接
    - 健康检测

    不负责：
    - GUI 状态切换
    - QThread/QTimer
    - 自动点击
    - 截图识别
    - 后台命令
    - 自动重连
    - 多窗口会话管理
    """

    def __init__(self):
        """初始化窗口管理器，设置默认内部状态。"""
        self._connected_window: Optional[ConnectedWindow] = None
        """当前连接窗口，None 表示未连接"""
        self._last_window_info: Optional[WindowInfo] = None
        """最近一次连接使用的搜索结果"""
        self._last_error: str = ""
        """最近一次错误信息"""

    def search_windows(self, keyword: str) -> list[WindowInfo]:
        """
        搜索匹配关键词的可见窗口。

        匹配范围：
        - 窗口标题
        - 进程名称
        - PID

        P0-02 阶段仅保留接口和基础检查。
        真实 Windows API 搜索逻辑在 P0-03 阶段实现。
        """
        error = self._ensure_supported()
        if error:
            self._set_error(error)
            return []

        keyword = keyword.strip()
        if not keyword:
            return []

        logger.info("开始搜索窗口，关键词：%s", keyword)

        # P0-03 阶段实现真实搜索逻辑
        logger.info("搜索窗口完成，结果数量：0")
        return []

    def connect_window(
        self,
        window: WindowInfo,
        options: Optional[ConnectOptions] = None,
    ) -> ConnectResult:
        """
        连接指定窗口。

        Args:
            window: 搜索结果中的窗口信息。
            options: 连接选项，为 None 时使用默认选项。

        Returns:
            ConnectResult

        P0-02 阶段仅保留接口和基础检查。
        真实连接逻辑在 P0-04 ~ P0-07 阶段实现。
        """
        error = self._ensure_supported()
        if error:
            self._set_error(error)
            return ConnectResult.fail(error)

        if window is None:
            message = "未选择窗口"
            self._set_error(message)
            return ConnectResult.fail(message)

        options = options or ConnectOptions()

        logger.info(
            "开始连接窗口：title=%s, process_name=%s, pid=%s, hwnd=%s, control_mode=%s",
            window.title,
            window.process_name,
            window.pid,
            window.hwnd,
            options.control_mode.value,
        )

        # P0-04 ~ P0-07 阶段实现真实连接逻辑
        message = "窗口连接功能尚未实现"
        self._set_error(message)
        return ConnectResult.fail(message)

    def disconnect_window(self) -> None:
        """
        断开当前连接，清理内部状态。

        注意：
        - 不关闭游戏窗口
        - 不最小化游戏窗口
        - 不改变游戏前台状态
        - 不发送任何输入
        - _last_window_info 保留不清空，用于调试和后续重连
        """
        if self._connected_window is not None:
            logger.info(
                "断开窗口连接：title=%s, pid=%s, hwnd=%s",
                self._connected_window.title,
                self._connected_window.pid,
                self._connected_window.hwnd,
            )
        else:
            logger.info("断开窗口连接：当前未连接")

        self._connected_window = None
        self._last_error = ""

    def check_health(self) -> HealthCheckResult:
        """
        检测当前连接窗口是否正常。

        P0-02 阶段：
        - 未连接返回 NOT_CONNECTED
        - 已连接暂时返回 HEALTHY

        真实健康检测逻辑在 P1-01 阶段实现。
        """
        if self._connected_window is None:
            return HealthCheckResult(
                status=HealthStatus.NOT_CONNECTED,
                message="未连接",
                window=None,
            )

        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="连接正常",
            window=self._connected_window,
        )

    def get_connected_window(self) -> Optional[ConnectedWindow]:
        """
        获取当前已连接窗口。

        Returns:
            未连接时返回 None。
        """
        return self._connected_window

    def get_last_error(self) -> str:
        """
        获取最近一次错误信息。
        """
        return self._last_error

    def get_last_window_info(self) -> Optional[WindowInfo]:
        """
        获取最近一次连接使用的搜索结果。
        """
        return self._last_window_info

    def is_supported(self) -> bool:
        """
        当前运行环境是否支持窗口连接能力。
        """
        return self._ensure_supported() is None

    def get_unsupported_reason(self) -> str:
        """
        获取当前运行环境不支持窗口连接能力的原因。
        """
        return self._ensure_supported() or ""

    def _ensure_supported(self) -> Optional[str]:
        """
        检查当前环境是否支持窗口连接能力。

        每次调用实时检查，不缓存结果。

        Returns:
            None 表示支持。
            str 表示不支持原因。
        """
        if not IS_WINDOWS:
            return "当前窗口连接功能仅支持 Windows 10 / Windows 11"

        if win32gui is None or win32process is None or psutil is None:
            return "缺少窗口连接依赖，请安装 pywin32 和 psutil"

        return None

    def _set_error(self, message: str) -> None:
        """统一设置最近错误信息并记录日志。

        同时更新 _last_error 和输出 warning 日志，
        避免调用方重复写两处。

        Args:
            message: 错误信息
        """
        self._last_error = message
        logger.warning(message)

