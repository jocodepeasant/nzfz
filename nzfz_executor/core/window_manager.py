"""窗口管理器：执行器窗口连接核心管理类。

提供窗口搜索、连接、断开、健康检测的统一接口，屏蔽 Windows API 细节。
"""

from __future__ import annotations

import logging
import platform
import time
from typing import Optional

from nzfz_executor.core.models import (
    WindowInfo,
    WindowRect,
    ConnectedWindow,
    ConnectOptions,
    ConnectResult,
    ControlMode,
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

    MIN_WINDOW_WIDTH = 200
    MIN_WINDOW_HEIGHT = 150

    CONNECT_MIN_WINDOW_WIDTH = 100
    CONNECT_MIN_WINDOW_HEIGHT = 100
    MIN_CLIENT_WIDTH = 100
    MIN_CLIENT_HEIGHT = 100

    ACTIVATE_RETRY_COUNT = 2
    ACTIVATE_RETRY_INTERVAL = 0.1

    def __init__(self):
        """初始化窗口管理器，设置默认内部状态。"""
        self._connected_window: Optional[ConnectedWindow] = None
        """当前连接窗口，None 表示未连接"""
        self._last_window_info: Optional[WindowInfo] = None
        """最近一次连接使用的搜索结果"""
        self._last_error: str | None = None
        """最近一次错误信息，None 表示无错误"""

    def search_windows(self, keyword: str) -> list[WindowInfo]:
        """
        搜索匹配关键词的可见窗口。

        匹配范围：
        - 窗口标题
        - 进程名称
        - PID
        """
        keyword = (keyword or "").strip()
        if not keyword:
            self._last_error = None
            return []

        error = self._ensure_supported()
        if error:
            self._set_error(error)
            return []

        logger.info("开始搜索窗口，关键词：%s", keyword)

        results: list[WindowInfo] = []

        def _enum_callback(hwnd: int, _lparam: int) -> bool:
            info = self._build_window_info_if_match(hwnd, keyword)
            if info is not None:
                results.append(info)
            return True

        try:
            win32gui.EnumWindows(_enum_callback, 0)
        except Exception as exc:
            self._last_error = str(exc)
            logger.error("枚举窗口失败：%s", exc)
            return results

        results.sort(key=lambda item: item.match_score, reverse=True)
        self._last_error = None

        logger.info("搜索窗口完成，结果数量：%d", len(results))
        return results

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

        P0-04：连接前校验 → P0-05：构建候选上下文 → P0-06（可选）激活窗口 → 保存连接状态。
        P0-06 仅在 options.activate_on_connect=True 时执行。
        """
        options = options or ConnectOptions()

        logger.info("开始连接窗口...")

        if self._connected_window is not None:
            msg = "连接失败：当前已连接窗口，请先断开后再连接其他窗口"
            self._last_error = msg
            logger.warning(msg)
            return ConnectResult.fail(msg)

        ok, error = self._validate_window_for_connect(window, options)
        if not ok:
            self._last_error = error
            logger.warning(error)
            return ConnectResult.fail(error)

        ok, error, candidate = self._build_connected_window(window)
        if not ok:
            self._last_error = error
            logger.warning(error)
            return ConnectResult.fail(error)

        activated = False
        if options.activate_on_connect:
            ok, error = self._activate_window(window.hwnd)
            if not ok:
                self._last_error = error
                logger.warning(error)
                return ConnectResult.fail(error)
            activated = True
        else:
            logger.info("跳过窗口激活: activate_on_connect=False")

        self._connected_window = candidate
        self._last_window_info = window
        self._last_error = None
        logger.info(
            "窗口连接成功: title=%s, pid=%s, hwnd=%s, client=%s, activated=%s",
            candidate.title,
            candidate.pid,
            candidate.hwnd,
            candidate.client_size_text,
            activated,
        )
        return ConnectResult.ok(candidate, activated=activated)

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
            logger.debug("disconnect_window called, but no window is connected")

        self._connected_window = None
        self._last_error = None

    def is_connected(self) -> bool:
        """判断当前是否存在已连接窗口（不执行健康检测）。"""
        return self._connected_window is not None

    @property
    def connected_window(self) -> ConnectedWindow | None:
        """当前已连接窗口上下文，未连接时返回 None。"""
        return self._connected_window

    @property
    def last_error(self) -> str | None:
        """最近一次 Core 操作产生的错误信息，None 表示无错误。"""
        return self._last_error

    @property
    def last_window_info(self) -> WindowInfo | None:
        """最近一次连接使用的 WindowInfo 搜索快照（不代表当前仍连接）。"""
        return self._last_window_info

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

    def get_connected_window(self) -> ConnectedWindow | None:
        """获取当前已连接窗口。"""
        return self.connected_window

    def get_last_error(self) -> str | None:
        """获取最近一次错误信息。"""
        return self.last_error

    def get_last_window_info(self) -> WindowInfo | None:
        """获取最近一次连接使用的搜索结果。"""
        return self.last_window_info

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

    def _log_unsupported_options(self, options: ConnectOptions) -> None:
        """记录当前版本不支持的连接选项配置日志。"""
        if options.restore_if_minimized:
            logger.info("当前版本暂不支持自动恢复最小化窗口")

        if options.control_mode != ControlMode.FOREGROUND:
            logger.info(
                "当前版本暂不支持非前台控制，仍按 FOREGROUND 流程连接: mode=%s",
                options.control_mode,
            )

    def _validate_window_for_connect(
        self, window: WindowInfo, options: ConnectOptions
    ) -> tuple[bool, str]:
        """连接前窗口有效性校验。

        按以下顺序逐项校验，任意一步不通过立即返回 (False, error_message)：
        1. 记录不支持的选项配置日志
        2. 运行平台校验（仅 Windows 支持）
        3. 依赖库可用性校验（win32gui、psutil）
        4. 窗口信息非空校验
        5. 窗口句柄有效性校验
        6. PID 有效性校验
        7. 窗口句柄存活校验（IsWindow）
        8. 进程一致性校验（PID 未变化）
        9. 进程状态校验（存在、可访问、非僵尸）
        10. 进程运行状态校验
        11. 进程名称非空校验
        12. 窗口可见性校验
        13. 窗口最小化状态校验
        14. 窗口标题非空校验
        15. 全部通过返回 (True, "")

        Args:
            window: 搜索结果中的窗口信息
            options: 连接选项

        Returns:
            (是否通过, 错误信息) 元组
        """
        try:
            # 1. 记录不支持的选项配置日志
            self._log_unsupported_options(options)

            # 2. 检查运行平台：仅支持 Windows
            if not IS_WINDOWS:
                return False, "连接失败：当前平台不支持真实窗口连接"

            # 3. 检查依赖库可用性
            if win32gui is None:
                return False, "连接失败：缺少 pywin32 依赖"
            if psutil is None:
                return False, "连接失败：缺少 psutil 依赖"

            # 4. 窗口信息非空校验
            if window is None:
                return False, "连接失败：窗口信息为空"

            # 5. 窗口句柄有效性校验
            if window.hwnd <= 0:
                return False, "连接失败：窗口句柄无效"

            # 6. PID 有效性校验
            if window.pid <= 0:
                return False, "连接失败：窗口 PID 无效"

            # 7. 窗口句柄存活校验
            if not win32gui.IsWindow(window.hwnd):
                return False, "连接失败：窗口句柄已失效，请重新搜索"

            # 8. 进程一致性校验：获取当前实际 PID，与搜索结果中的 PID 对比
            _, current_pid = win32process.GetWindowThreadProcessId(window.hwnd)
            if current_pid != window.pid:
                return False, "连接失败：窗口进程已变化，请重新搜索"

            # 9. 进程状态校验：通过 psutil 获取进程对象，捕获各类异常
            try:
                process = psutil.Process(current_pid)
            except psutil.NoSuchProcess:
                return False, "连接失败：目标进程不存在"
            except psutil.AccessDenied:
                return False, "连接失败：无法访问目标进程信息"
            except psutil.ZombieProcess:
                return False, "连接失败：目标进程状态异常"

            # 10. 进程运行状态校验
            if not process.is_running():
                return False, "连接失败：目标进程未运行"

            # 11. 进程名称非空校验
            if not process.name() or not process.name().strip():
                return False, "连接失败：无法获取目标进程名称"

            # 12. 窗口可见性校验
            if not win32gui.IsWindowVisible(window.hwnd):
                return False, "连接失败：窗口不可见"

            # 13. 窗口最小化状态校验
            if win32gui.IsIconic(window.hwnd):
                return False, "连接失败：窗口已最小化，请恢复窗口后重试"

            # 14. 窗口标题非空校验
            title = win32gui.GetWindowText(window.hwnd).strip()
            if not title:
                return False, "连接失败：窗口标题为空，请重新搜索"

            return True, ""

        except Exception as exc:
            logger.exception("连接前校验异常：%s", exc)
            return False, f"连接失败：连接前校验异常：{exc}"

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

    @staticmethod
    def _calculate_match_score(keyword: str, title: str, process_name: str, pid: int) -> float:
        """
        计算窗口与关键词的匹配分数。

        匹配范围：PID > 窗口标题 > 进程名称。

        Args:
            keyword: 用户输入的搜索关键词
            title: 窗口标题
            process_name: 窗口所属进程名称
            pid: 窗口所属进程 ID

        Returns:
            0.0 ~ 1.0 的匹配分数，0.0 表示不匹配
        """
        keyword = (keyword or "").lower().strip()
        title_lower = (title or "").lower()
        process_lower = (process_name or "").lower()

        if not keyword:
            return 0.0

        if keyword.isdigit() and int(keyword) == pid:
            return 1.0

        if title_lower == keyword:
            return 1.0

        if keyword in title_lower:
            return 0.8

        if process_lower == keyword:
            return 0.95

        if keyword in process_lower:
            return 0.8

        return 0.0

    def _get_process_name(self, pid: int) -> Optional[str]:
        """
        通过 PID 获取进程名称。

        Args:
            pid: 进程 ID

        Returns:
            进程名称，获取失败或名称为空时返回 None
        """
        try:
            name = psutil.Process(pid).name()
            if name and name.strip():
                return name.strip()
            return None
        except Exception as exc:
            logger.debug("获取进程名失败，pid=%s，错误：%s", pid, exc)
            return None

    def _get_search_window_rect(self, hwnd: int, is_minimized: bool) -> Optional[WindowRect]:
        """
        获取搜索阶段窗口矩形。

        非最小化窗口使用 GetWindowRect，最小化窗口使用 GetWindowPlacement 获取恢复矩形，
        并校验窗口尺寸是否满足最小阈值。

        Args:
            hwnd: 窗口句柄
            is_minimized: 窗口是否处于最小化状态

        Returns:
            有效的 WindowRect，获取失败或尺寸不满足阈值时返回 None
        """
        try:
            if not is_minimized:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                rect = WindowRect(left, top, right, bottom)
            else:
                placement = win32gui.GetWindowPlacement(hwnd)
                left, top, right, bottom = placement[4]
                rect = WindowRect(left, top, right, bottom)

            if not rect.is_valid(min_width=self.MIN_WINDOW_WIDTH, min_height=self.MIN_WINDOW_HEIGHT):
                return None

            return rect
        except Exception as exc:
            logger.debug(
                "获取搜索窗口矩形失败，hwnd=%s, is_minimized=%s, 错误：%s",
                hwnd,
                is_minimized,
                exc,
            )
            return None

    def _build_window_info_if_match(self, hwnd: int, keyword: str) -> Optional[WindowInfo]:
        """
        校验窗口并构造 WindowInfo，不匹配时返回 None。

        校验顺序：
        1. 窗口句柄有效性
        2. 窗口可见性（不可见直接跳过）
        3. 窗口标题非空
        4. 窗口最小化状态
        5. 窗口矩形有效（尺寸满足最小阈值）
        6. PID 有效
        7. 进程名称非空
        8. 匹配分数 > 0

        Args:
            hwnd: 窗口句柄
            keyword: 用户搜索关键词

        Returns:
            匹配成功时返回 WindowInfo，否则返回 None
        """
        try:
            if not win32gui.IsWindow(hwnd):
                return None

            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            if not is_visible:
                return None

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return None

            is_minimized = bool(win32gui.IsIconic(hwnd))

            rect = self._get_search_window_rect(hwnd, is_minimized)
            if rect is None:
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None

            process_name = self._get_process_name(pid)
            if not process_name:
                return None

            match_score = self._calculate_match_score(keyword, title, process_name, pid)
            if match_score <= 0:
                return None

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                pid=pid,
                width=rect.width,
                height=rect.height,
                match_score=match_score,
                is_visible=is_visible,
                is_minimized=is_minimized,
            )
        except Exception as exc:
            logger.debug("构造窗口搜索结果失败，hwnd=%s，错误：%s", hwnd, exc)
            return None

    def _get_dpi_scale(self, hwnd: int) -> float:
        """获取窗口 DPI 缩放比例，当前版本固定返回 1.0。"""
        del hwnd
        return 1.0

    def _build_connected_window(
        self,
        window: WindowInfo,
    ) -> tuple[bool, str, Optional[ConnectedWindow]]:
        """构建 ConnectedWindow 候选对象，不写入 _connected_window。"""
        try:
            hwnd = window.hwnd

            if not win32gui.IsWindow(hwnd):
                return False, "连接失败：窗口句柄已失效，请重新搜索", None

            if not win32gui.IsWindowVisible(hwnd):
                return False, "连接失败：窗口不可见", None

            if win32gui.IsIconic(hwnd):
                return False, "连接失败：窗口已最小化，请恢复窗口后重试", None

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return False, "连接失败：窗口标题为空，请重新搜索", None

            _, current_pid = win32process.GetWindowThreadProcessId(hwnd)
            if current_pid != window.pid:
                return False, "连接失败：窗口进程已变化，请重新搜索", None

            try:
                process_name = psutil.Process(current_pid).name()
                if not process_name or not process_name.strip():
                    return False, "连接失败：无法获取目标进程名称", None
                process_name = process_name.strip()
            except psutil.NoSuchProcess:
                return False, "连接失败：目标进程不存在", None
            except psutil.AccessDenied:
                return False, "连接失败：无法访问目标进程信息", None
            except psutil.ZombieProcess:
                return False, "连接失败：目标进程状态异常", None

            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            except Exception as exc:
                logger.debug("获取窗口矩形失败，hwnd=%s，错误：%s", hwnd, exc)
                return False, "连接失败：获取窗口矩形失败", None

            window_rect = WindowRect(left, top, right, bottom)
            if window_rect.width < self.CONNECT_MIN_WINDOW_WIDTH:
                return False, "连接失败：窗口宽度过小", None
            if window_rect.height < self.CONNECT_MIN_WINDOW_HEIGHT:
                return False, "连接失败：窗口高度过小", None

            try:
                c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
                s_left, s_top = win32gui.ClientToScreen(hwnd, (c_left, c_top))
                s_right, s_bottom = win32gui.ClientToScreen(hwnd, (c_right, c_bottom))
            except Exception as exc:
                logger.debug("获取客户区矩形失败，hwnd=%s，错误：%s", hwnd, exc)
                return False, "连接失败：获取客户区矩形失败", None

            client_rect = WindowRect(
                left=s_left,
                top=s_top,
                right=s_right,
                bottom=s_bottom,
            )
            if client_rect.width < self.MIN_CLIENT_WIDTH:
                return False, "连接失败：客户区宽度过小", None
            if client_rect.height < self.MIN_CLIENT_HEIGHT:
                return False, "连接失败：客户区高度过小", None

            connected_window = ConnectedWindow(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                pid=current_pid,
                window_rect=window_rect,
                client_rect=client_rect,
                dpi_scale=self._get_dpi_scale(hwnd),
            )
            return True, "", connected_window

        except Exception as exc:
            logger.exception("构建连接上下文异常")
            return False, f"连接失败：构建连接上下文异常：{exc}", None

    def _activate_window(self, hwnd: int) -> tuple[bool, str]:
        """尝试将目标窗口切换到前台，以 GetForegroundWindow 校验结果为准。"""
        try:
            if hwnd <= 0:
                return False, "激活失败：窗口句柄无效"

            if not win32gui.IsWindow(hwnd):
                return False, "激活失败：窗口句柄已失效"

            if win32gui.IsIconic(hwnd):
                return False, "激活失败：窗口已最小化，请恢复窗口后重试"

            if win32gui.GetForegroundWindow() == hwnd:
                logger.info("目标窗口已经是前台窗口: hwnd=%s", hwnd)
                return True, ""

            for index in range(self.ACTIVATE_RETRY_COUNT):
                logger.info(
                    "尝试激活目标窗口: hwnd=%s, attempt=%s",
                    hwnd,
                    index + 1,
                )
                try:
                    win32gui.BringWindowToTop(hwnd)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception as exc:
                    logger.warning(
                        "调用窗口激活 API 异常: hwnd=%s, attempt=%s, error=%s",
                        hwnd,
                        index + 1,
                        exc,
                    )

                time.sleep(self.ACTIVATE_RETRY_INTERVAL)

                if win32gui.GetForegroundWindow() == hwnd:
                    logger.info("目标窗口激活成功: hwnd=%s", hwnd)
                    return True, ""

            foreground = win32gui.GetForegroundWindow()
            logger.warning(
                "目标窗口激活失败，前台窗口不是目标窗口: hwnd=%s, foreground=%s",
                hwnd,
                foreground,
            )
            return (
                False,
                "激活失败：目标窗口未成为前台窗口，可能被系统限制或权限不足",
            )

        except Exception as exc:
            logger.exception("窗口激活异常")
            return False, f"激活失败：窗口激活异常：{exc}"

