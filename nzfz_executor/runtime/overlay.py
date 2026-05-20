"""窗口叠加层：在目标窗口上绘制操作标记与日志信息。"""

from __future__ import annotations


class OverlayRenderer:
    """叠加层渲染器：在目标窗口上显示点击标记、按键信息与操作日志。"""

    def show(self, hwnd: int, info: str = "") -> bool:
        """在指定窗口上显示叠加层。

        Args:
            hwnd: 目标窗口句柄。
            info: 叠加层初始显示信息。

        Returns:
            显示成功返回 True，否则返回 False。
        """
        raise NotImplementedError

    def hide(self) -> bool:
        """隐藏叠加层。

        Returns:
            隐藏成功返回 True，否则返回 False。
        """
        raise NotImplementedError

    def draw_click_marker(self, x: int, y: int, duration_ms: int = 1500) -> None:
        """在指定坐标绘制点击标记。

        Args:
            x: 标记横坐标。
            y: 标记纵坐标。
            duration_ms: 标记显示时长（毫秒）。
        """
        raise NotImplementedError

    def draw_key_info(self, key: str, hold_ms: int = 0, duration_ms: int = 2000) -> None:
        """绘制按键信息提示。

        Args:
            key: 按键名称。
            hold_ms: 按住时长（毫秒），0 表示短按。
            duration_ms: 提示显示时长（毫秒）。
        """
        raise NotImplementedError

    def log_operation(self, msg: str) -> None:
        """在叠加层上记录操作日志。

        Args:
            msg: 日志消息内容。
        """
        raise NotImplementedError