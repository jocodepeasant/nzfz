"""输入模拟：提供鼠标点击、键盘按键与拖拽操作。"""

from __future__ import annotations


class InputController:
    """输入控制器：封装鼠标与键盘的模拟输入操作。"""

    def click(self, x: int, y: int, button: str = "left", hwnd: int = 0) -> None:
        """在指定坐标执行鼠标点击。

        Args:
            x: 目标横坐标。
            y: 目标纵坐标。
            button: 鼠标按键，"left" / "right" / "middle"。
            hwnd: 目标窗口句柄，0 表示桌面坐标。
        """
        raise NotImplementedError

    def press_key(self, key: str, hold_ms: int = 0, hwnd: int = 0) -> None:
        """模拟键盘按键。

        Args:
            key: 按键名称，如 "a"、"enter"、"space"。
            hold_ms: 按住时长（毫秒），0 表示短按。
            hwnd: 目标窗口句柄，0 表示前台窗口。
        """
        raise NotImplementedError

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration_ms: int = 600,
    ) -> None:
        """从起点拖拽至终点。

        Args:
            from_x: 起点横坐标。
            from_y: 起点纵坐标。
            to_x: 终点横坐标。
            to_y: 终点纵坐标。
            duration_ms: 拖拽持续时间（毫秒）。
        """
        raise NotImplementedError