"""P2-11 前台窗口检查单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.foreground import (
    check_foreground_window,
    warn_if_not_foreground,
)
from nzfz_executor.core.models import ConnectedWindow, WindowRect


def _connected(hwnd: int = 100) -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=hwnd,
        title="Target",
        process_name="game.exe",
        pid=1,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


class TestForegroundCheck:
    def test_is_foreground_when_hwnd_matches(self, monkeypatch) -> None:
        monkeypatch.setitem(
            __import__("sys").modules,
            "win32gui",
            type(
                "FakeWin32Gui",
                (),
                {
                    "GetForegroundWindow": staticmethod(lambda: 100),
                    "GetWindowText": staticmethod(lambda hwnd: f"title-{hwnd}"),
                },
            )(),
        )
        result = check_foreground_window(_connected(100))

        assert result.is_foreground is True

    def test_not_foreground_when_hwnd_differs(self, monkeypatch) -> None:
        monkeypatch.setitem(
            __import__("sys").modules,
            "win32gui",
            type(
                "FakeWin32Gui",
                (),
                {
                    "GetForegroundWindow": staticmethod(lambda: 200),
                    "GetWindowText": staticmethod(lambda hwnd: f"title-{hwnd}"),
                },
            )(),
        )
        result = check_foreground_window(_connected(100))

        assert result.is_foreground is False
        assert result.foreground_hwnd == 200

    def test_warn_if_not_foreground_logs_warning(self, monkeypatch) -> None:
        monkeypatch.setitem(
            __import__("sys").modules,
            "win32gui",
            type(
                "FakeWin32Gui",
                (),
                {
                    "GetForegroundWindow": staticmethod(lambda: 200),
                    "GetWindowText": staticmethod(lambda hwnd: f"title-{hwnd}"),
                },
            )(),
        )
        logs: list[str] = []
        warn_if_not_foreground(_connected(100), logs.append)

        assert any("[Safety][Warning]" in line for line in logs)
        assert any("target hwnd=100" in line for line in logs)

    def test_warn_if_foreground_no_log(self, monkeypatch) -> None:
        monkeypatch.setitem(
            __import__("sys").modules,
            "win32gui",
            type(
                "FakeWin32Gui",
                (),
                {
                    "GetForegroundWindow": staticmethod(lambda: 100),
                    "GetWindowText": staticmethod(lambda hwnd: "Target"),
                },
            )(),
        )
        logs: list[str] = []
        warn_if_not_foreground(_connected(100), logs.append)

        assert logs == []
