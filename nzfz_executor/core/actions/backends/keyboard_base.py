"""键盘输入后端协议（P2-11）。"""

from __future__ import annotations

from typing import Protocol


class KeyboardInputBackend(Protocol):
    """键盘输入后端协议。"""

    def press(self, key: str, hold_ms: int = 0) -> None:
        ...
