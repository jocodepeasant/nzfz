"""输入操作抽象层：统一封装鼠标与键盘操作。"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod


class InputAdapter(ABC):
    """输入适配器抽象基类。"""

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        ...

    @abstractmethod
    def key_press(self, key: str) -> None:
        ...

    @abstractmethod
    def key_hold(self, key: str, hold_ms: int) -> None:
        ...

    @abstractmethod
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int,
    ) -> None:
        ...

    @abstractmethod
    def scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        ...


class PynputAdapter(InputAdapter):
    """基于 pynput 的输入适配器。"""

    def click(self, x: int, y: int) -> None:
        from pynput.mouse import Button, Controller as MouseController

        mouse = MouseController()
        mouse.position = (x, y)
        time.sleep(0.02)
        mouse.click(Button.left)

    def key_press(self, key: str) -> None:
        from pynput.keyboard import Controller as KeyboardController

        kb = KeyboardController()
        kb.press(key)
        kb.release(key)

    def key_hold(self, key: str, hold_ms: int) -> None:
        from pynput.keyboard import Controller as KeyboardController

        kb = KeyboardController()
        kb.press(key)
        time.sleep(hold_ms / 1000)
        kb.release(key)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int,
    ) -> None:
        from pynput.mouse import Button, Controller as MouseController

        mouse = MouseController()
        mouse.position = (start_x, start_y)
        time.sleep(0.02)
        mouse.press(Button.left)
        steps = max(duration_ms // 10, 1)
        step_delay = duration_ms / 1000 / steps
        for i in range(1, steps + 1):
            t = i / steps
            cx = int(start_x + (end_x - start_x) * t)
            cy = int(start_y + (end_y - start_y) * t)
            mouse.position = (cx, cy)
            time.sleep(step_delay)
        mouse.release(Button.left)

    def scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        from pynput.mouse import Controller as MouseController

        mouse = MouseController()
        mouse.position = (x, y)
        time.sleep(0.02)
        mouse.scroll(dx, dy)


class PyautoguiAdapter(InputAdapter):
    """基于 pyautogui 的输入适配器。"""

    def click(self, x: int, y: int) -> None:
        import pyautogui

        pyautogui.click(x=x, y=y)

    def key_press(self, key: str) -> None:
        import pyautogui

        pyautogui.press(key)

    def key_hold(self, key: str, hold_ms: int) -> None:
        import pyautogui

        pyautogui.keyDown(key)
        time.sleep(hold_ms / 1000)
        pyautogui.keyUp(key)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int,
    ) -> None:
        import pyautogui

        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration_ms / 1000,
        )

    def scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        import pyautogui

        pyautogui.moveTo(x, y)
        if dy != 0:
            pyautogui.scroll(dy)
        if dx != 0:
            pyautogui.hscroll(dx)


def create_input_adapter(backend: str = "pynput") -> InputAdapter:
    """创建输入适配器实例，按优先级回退。"""
    if backend == "pynput":
        try:
            import pynput  # noqa: F401

            return PynputAdapter()
        except ImportError:
            pass
        try:
            import pyautogui  # noqa: F401

            return PyautoguiAdapter()
        except ImportError:
            raise RuntimeError("未找到可用的输入后端（pynput / pyautogui）")
    if backend == "pyautogui":
        try:
            import pyautogui  # noqa: F401

            return PyautoguiAdapter()
        except ImportError:
            pass
        try:
            import pynput  # noqa: F401

            return PynputAdapter()
        except ImportError:
            raise RuntimeError("未找到可用的输入后端（pyautogui / pynput）")
    raise ValueError(f"不支持的输入后端: {backend}")
