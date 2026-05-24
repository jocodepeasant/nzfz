"""Dry-run 键盘输入后端（P2-11）。"""

from __future__ import annotations


class DryRunKeyboardBackend:
    """跳过真实按键。"""

    def press(self, key: str, hold_ms: int = 0) -> None:
        return
