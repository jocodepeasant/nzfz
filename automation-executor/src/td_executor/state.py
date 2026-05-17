"""对局状态管理（占位）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from td_executor.runtime.window import WindowRect


class GameState:
    """Tracks wave, resources, HP, UI flags; implementation pending."""

    wave: int | None = None
    window_handle: int | None = None
    window_rect: WindowRect | None = None
    is_focused: bool = False

    def update_window(self, rect: WindowRect, focused: bool = True) -> None:
        self.window_handle = rect.hwnd
        self.window_rect = rect
        self.is_focused = focused

    def clear_window(self) -> None:
        self.window_handle = None
        self.window_rect = None
        self.is_focused = False
