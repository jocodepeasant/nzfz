"""窗口管理：定义窗口信息数据类与窗口管理器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nzfz_executor.core.models import ConnectedWindow


@dataclass
class WindowInfo:
    """窗口信息数据类，封装窗口句柄、位置、尺寸及标题。"""

    hwnd: int
    left: int
    top: int
    width: int
    height: int
    title: str = ""


def from_connected_window(connected: ConnectedWindow) -> WindowInfo:
    """将 core 层 ConnectedWindow 转换为 runtime 层 WindowInfo。"""
    rect = connected.client_rect
    return WindowInfo(
        hwnd=connected.hwnd,
        left=rect.left,
        top=rect.top,
        width=rect.width,
        height=rect.height,
        title=connected.title,
    )


class WindowManager:
    """窗口管理器：提供窗口查找、聚焦、枚举等操作。"""

    def find_window(self, title_keyword: str) -> WindowInfo | None:
        """根据标题关键字查找窗口，返回首个匹配的窗口信息，未找到则返回 None。"""
        raise NotImplementedError

    def focus_window(self, hwnd: int) -> bool:
        """将指定窗口设为前台焦点，成功返回 True。"""
        raise NotImplementedError

    def get_window_rect(self, hwnd: int) -> WindowInfo | None:
        """获取指定窗口的位置与尺寸信息，窗口无效时返回 None。"""
        raise NotImplementedError

    def is_window_valid(self, hwnd: int) -> bool:
        """判断指定窗口句柄是否仍然有效。"""
        raise NotImplementedError

    def list_windows(self, title_keyword: str) -> list[dict]:
        """枚举所有标题包含指定关键字的窗口，返回字典列表。"""
        raise NotImplementedError
