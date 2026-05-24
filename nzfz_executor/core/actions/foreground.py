"""前台窗口检查（P2-11）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nzfz_executor.core.models import ConnectedWindow


@dataclass(frozen=True)
class ForegroundCheckResult:
    is_foreground: bool
    target_hwnd: int
    foreground_hwnd: int
    target_title: str = ""
    foreground_title: str = ""


def check_foreground_window(context: ConnectedWindow) -> ForegroundCheckResult:
    try:
        import win32gui
    except ImportError:
        return ForegroundCheckResult(
            is_foreground=True,
            target_hwnd=context.hwnd,
            foreground_hwnd=context.hwnd,
            target_title=context.title,
            foreground_title=context.title,
        )

    target_hwnd = context.hwnd
    foreground_hwnd = win32gui.GetForegroundWindow()
    target_title = _safe_window_title(win32gui, target_hwnd) or context.title
    foreground_title = _safe_window_title(win32gui, foreground_hwnd)

    return ForegroundCheckResult(
        is_foreground=target_hwnd == foreground_hwnd,
        target_hwnd=target_hwnd,
        foreground_hwnd=foreground_hwnd,
        target_title=target_title,
        foreground_title=foreground_title,
    )


def warn_if_not_foreground(
    context: ConnectedWindow | None,
    log: Callable[[str], None] | None,
) -> None:
    if context is None or log is None:
        return

    result = check_foreground_window(context)
    if result.is_foreground:
        return

    log(
        "[Safety][Warning] 目标窗口当前不是前台，"
        "真实输入可能发送到错误窗口，继续执行",
    )
    log(
        f"[Safety] target hwnd={result.target_hwnd} title={result.target_title}",
    )
    log(
        f"[Safety] foreground hwnd={result.foreground_hwnd} "
        f"title={result.foreground_title}",
    )


def _safe_window_title(win32gui, hwnd: int) -> str:
    try:
        return win32gui.GetWindowText(hwnd) or ""
    except Exception:
        return ""
