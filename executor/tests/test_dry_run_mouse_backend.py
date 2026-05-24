"""P2-08 DryRunMouseBackend 单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.backends.dry_run_backend import DryRunMouseBackend
from nzfz_executor.core.actions.models import ClickAction, ScreenPoint
from nzfz_executor.core.models import ConnectedWindow, WindowRect


def _connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=1,
        title="Test",
        process_name="test.exe",
        pid=100,
        window_rect=WindowRect(100, 200, 900, 800),
        client_rect=WindowRect(100, 200, 900, 800),
    )


class TestDryRunMouseBackend:
    def test_click_success(self) -> None:
        backend = DryRunMouseBackend()
        result = backend.click(
            ClickAction(point=ScreenPoint(x=10, y=20)),
            context=_connected(),
        )

        assert result.success is True

    def test_click_message_contains_dry_run(self) -> None:
        backend = DryRunMouseBackend()
        result = backend.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert "dry-run" in result.message

    def test_click_message_contains_button(self) -> None:
        backend = DryRunMouseBackend()
        result = backend.click(ClickAction(point=ScreenPoint(x=10, y=20)))

        assert "button=left" in result.message

    def test_context_none_still_success(self) -> None:
        backend = DryRunMouseBackend()
        result = backend.click(
            ClickAction(point=ScreenPoint(x=9999, y=9999)),
            context=None,
        )

        assert result.success is True

    def test_outside_window_still_success(self) -> None:
        backend = DryRunMouseBackend()
        result = backend.click(
            ClickAction(point=ScreenPoint(x=9999, y=9999)),
            context=_connected(),
        )

        assert result.success is True
