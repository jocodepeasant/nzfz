"""窗口连接数据模型：定义执行器窗口连接模块所需的基础数据结构。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class WindowRect:
    """
    Windows 窗口矩形。

    坐标约定：
    - left/top/right/bottom 均为屏幕坐标
    - width = right - left
    - height = bottom - top
    """

    left: int
    """左上角屏幕 X 坐标"""
    top: int
    """左上角屏幕 Y 坐标"""
    right: int
    """右下角屏幕 X 坐标"""
    bottom: int
    """右下角屏幕 Y 坐标"""

    @property
    def width(self) -> int:
        """宽度"""
        return self.right - self.left

    @property
    def height(self) -> int:
        """高度"""
        return self.bottom - self.top

    @property
    def size_text(self) -> str:
        """尺寸显示文本，例如 1280×720"""
        return f"{self.width}×{self.height}"

    def is_valid(self, min_width: int = 1, min_height: int = 1) -> bool:
        """判断尺寸是否有效。

        Args:
            min_width: 最小宽度阈值，默认 1
            min_height: 最小高度阈值，默认 1

        Returns:
            True 表示尺寸满足最小阈值
        """
        return self.width >= min_width and self.height >= min_height


@dataclass(frozen=True)
class WindowInfo:
    """
    搜索结果中的窗口信息。

    注意：
    - 这是搜索时的窗口快照
    - 不代表窗口当前仍然有效
    - 连接前必须重新校验 hwnd、pid、可见性、最小化状态和尺寸
    """

    hwnd: int
    """Windows 窗口句柄"""
    title: str
    """窗口标题"""
    process_name: str
    """进程名"""
    pid: int
    """进程 ID"""
    width: int
    """搜索时窗口宽度"""
    height: int
    """搜索时窗口高度"""
    match_score: float
    """匹配分数"""
    is_visible: bool = True
    """搜索时是否可见"""
    is_minimized: bool = False
    """搜索时是否最小化"""

    @property
    def size_text(self) -> str:
        """尺寸显示文本，例如 1280×720"""
        return f"{self.width}×{self.height}"

    @property
    def display_name(self) -> str:
        """显示名称，例如 逆战 (nz.exe, PID: 1234)"""
        return f"{self.title} ({self.process_name}, PID: {self.pid})"


@dataclass
class ConnectedWindow:
    """
    当前已连接窗口上下文。

    后续截图、坐标换算、输入控制、自动化执行都应基于该对象。

    注意：
    - 使用普通 dataclass（非 frozen），允许健康检测刷新字段
    - 推荐健康检测时使用整体替换方式刷新
    """

    hwnd: int
    """当前连接窗口句柄"""
    title: str
    """当前窗口标题"""
    process_name: str
    """当前进程名"""
    pid: int
    """当前进程 ID"""
    window_rect: WindowRect
    """整个窗口矩形，屏幕坐标"""
    client_rect: WindowRect
    """客户区矩形，屏幕坐标"""
    dpi_scale: float = 1.0
    """DPI 缩放比例，当前默认 1.0"""
    connected_at: float = field(default_factory=time.time)
    """连接时间戳"""

    @property
    def window_size_text(self) -> str:
        """窗口矩形尺寸显示文本"""
        return self.window_rect.size_text

    @property
    def client_size_text(self) -> str:
        """客户区矩形尺寸显示文本"""
        return self.client_rect.size_text

    @property
    def display_name(self) -> str:
        """显示名称，例如 逆战 (nz.exe, PID: 1234)"""
        return f"{self.title} ({self.process_name}, PID: {self.pid})"


class HealthStatus(Enum):
    """窗口连接健康状态枚举，表示当前连接窗口的健康状况。"""

    HEALTHY = "healthy"
    """连接正常"""
    NOT_CONNECTED = "未连接"
    """当前未连接"""
    HANDLE_INVALID = "窗口句柄已失效"
    """窗口句柄已失效"""
    PROCESS_DEAD = "进程已退出"
    """进程已退出"""
    WINDOW_HIDDEN = "窗口不可见"
    """窗口不可见"""
    WINDOW_MINIMIZED = "窗口已最小化"
    """窗口已最小化"""
    WINDOW_SIZE_INVALID = "窗口尺寸异常"
    """窗口尺寸异常"""
    UNKNOWN = "未知异常"
    """未知异常"""


class ControlMode(Enum):
    """输入控制模式枚举，为后续后台控制能力预留。"""

    FOREGROUND = "foreground"
    """前台控制，需要激活窗口，兼容性较好"""
    BACKGROUND = "background"
    """后台控制，不主动激活窗口，游戏中不保证有效"""
    HYBRID = "hybrid"
    """混合控制，优先后台，失败时切换前台"""


@dataclass(frozen=True)
class ConnectOptions:
    """
    窗口连接选项。

    当前版本固定前台连接语义：
    - 默认连接时激活窗口
    - 最小化窗口不自动恢复
    - 当前版本不因 control_mode=BACKGROUND 跳过激活逻辑
    """

    activate_on_connect: bool = True
    """连接前是否激活窗口"""
    restore_if_minimized: bool = False
    """最小化时是否自动恢复（当前版本不启用）"""
    control_mode: ControlMode = ControlMode.FOREGROUND
    """控制模式"""


@dataclass
class ConnectResult:
    """
    窗口连接结果。

    用于 Core 层向 UI 层传递连接操作的结果。
    """

    success: bool
    """是否连接成功"""
    window: Optional[ConnectedWindow] = None
    """成功连接后的窗口对象"""
    error_message: str = ""
    """失败原因"""
    activated: bool = False
    """是否成功激活目标窗口"""

    @classmethod
    def ok(
        cls,
        window: ConnectedWindow,
        activated: bool = True,
    ) -> "ConnectResult":
        """创建连接成功的结果。

        Args:
            window: 连接成功的窗口对象
            activated: 是否成功激活

        Returns:
            连接成功结果
        """
        return cls(
            success=True,
            window=window,
            error_message="",
            activated=activated,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        activated: bool = False,
    ) -> "ConnectResult":
        """创建连接失败的结果。

        Args:
            message: 失败原因
            activated: 激活状态，默认 False

        Returns:
            连接失败结果
        """
        return cls(
            success=False,
            window=None,
            error_message=message,
            activated=activated,
        )


@dataclass
class HealthCheckResult:
    """
    窗口健康检测结果。

    用于向 UI 层传递当前连接窗口的健康状态。
    """

    status: HealthStatus
    """健康状态"""
    message: str = ""
    """状态描述"""
    window: Optional[ConnectedWindow] = None
    """刷新后的窗口对象"""

    @property
    def is_healthy(self) -> bool:
        """是否健康，等价于 status == HealthStatus.HEALTHY"""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_connected(self) -> bool:
        """是否存在连接上下文。

        注意：is_connected=True 不代表健康，只代表不是 NOT_CONNECTED。
        """
        return self.status != HealthStatus.NOT_CONNECTED