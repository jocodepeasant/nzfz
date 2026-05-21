"""窗口管理器 Mock 接口：提供窗口搜索、连接、断连及健康检测的抽象定义。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """窗口信息数据类，封装匹配到的窗口元数据及匹配度。"""

    title: str
    """窗口标题"""
    process_name: str
    """进程名称"""
    pid: int
    """进程ID"""
    width: int
    """窗口宽度（像素）"""
    height: int
    """窗口高度（像素）"""
    match_score: float = field(default=0.0)
    """匹配度分数（0.0 ~ 1.0），用于排序"""


class HealthStatus(str, Enum):
    """窗口连接健康状态枚举，反映当前窗口连接是否正常。"""

    HEALTHY = "healthy"
    """连接正常"""
    HANDLE_INVALID = "句柄已失效"
    """窗口句柄无效"""
    PROCESS_DEAD = "进程已退出"
    """进程不存在"""
    UNKNOWN = "未知异常"
    """其他异常"""


def search_windows(keyword: str) -> list[WindowInfo]:
    """模糊搜索所有匹配关键词的窗口。

    匹配范围包括窗口标题、进程名称，结果按 match_score 降序排列。

    Args:
        keyword: 搜索关键词，用于匹配窗口标题或进程名称。

    Returns:
        list[WindowInfo]: 匹配到的窗口信息列表（Mock 实现始终返回空列表）。
    """
    logger.debug("搜索窗口, keyword=%s", keyword)
    return []


def connect_window(window: WindowInfo) -> bool:
    """连接指定窗口，获取并保存窗口句柄。

    Args:
        window: 目标窗口的信息数据对象。

    Returns:
        bool: 连接成功返回 True，失败返回 False（Mock 实现始终返回 False）。
    """
    logger.info(
        "尝试连接窗口, title=%s, process_name=%s, pid=%s",
        window.title,
        window.process_name,
        window.pid,
    )
    return False


def disconnect_window() -> None:
    """断开当前连接，释放窗口句柄。

    Mock 实现无实际操作，仅记录日志。
    """
    logger.info("断开窗口连接")


def check_health() -> HealthStatus:
    """检测当前连接是否正常。

    同时检测窗口句柄有效性和进程存活状态。

    Returns:
        HealthStatus: 当前连接的健康状态（Mock 实现始终返回 HEALTHY）。
    """
    return HealthStatus.HEALTHY