"""P2-08 SendInputMouseBackend 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nzfz_executor.core.actions.backends.send_input_backend import (
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_MIDDLEUP,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
    SendInputMouseBackend,
)
from nzfz_executor.core.actions.models import ClickAction, MouseButton, MouseDragAction, ScreenPoint
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


def _click(
    x: int = 150,
    y: int = 250,
    button: MouseButton = MouseButton.LEFT,
    duration_ms: int = 50,
) -> ClickAction:
    return ClickAction(
        point=ScreenPoint(x=x, y=y),
        button=button,
        duration_ms=duration_ms,
    )


@pytest.fixture
def mock_user32():
    with patch("nzfz_executor.core.actions.backends.send_input_backend.ctypes.windll") as windll:
        user32 = MagicMock()
        windll.user32 = user32
        user32.SetCursorPos.return_value = 1
        user32.SendInput.return_value = 1
        yield user32


class TestSendInputMouseBackendSafety:
    def test_context_none_fails(self) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(), context=None)

        assert result.success is False
        assert "连接上下文为空" in result.message

    def test_outside_window_fails(self) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(
            _click(x=50, y=50),
            context=_connected(),
        )

        assert result.success is False
        assert "超出连接窗口范围" in result.message


class TestSendInputMouseBackendExecution:
    def test_inside_window_calls_set_cursor_pos(self, mock_user32) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(), context=_connected())

        assert result.success is True
        mock_user32.SetCursorPos.assert_called_once_with(150, 250)

    def test_set_cursor_pos_failure(self, mock_user32) -> None:
        mock_user32.SetCursorPos.return_value = 0
        backend = SendInputMouseBackend()
        result = backend.click(_click(), context=_connected())

        assert result.success is False
        assert "SetCursorPos" in result.message

    def test_send_input_failure(self, mock_user32) -> None:
        mock_user32.SendInput.return_value = 0
        backend = SendInputMouseBackend()
        result = backend.click(_click(), context=_connected())

        assert result.success is False
        assert "SendInput" in result.message

    def test_success_message(self, mock_user32) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(), context=_connected())

        assert result.success is True
        assert "真实点击完成" in result.message
        assert mock_user32.SendInput.call_count == 2


class TestSendInputMouseBackendButtons:
    def test_left_button_sends_down_and_up(self, mock_user32) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(button=MouseButton.LEFT), context=_connected())

        assert result.success is True
        assert mock_user32.SendInput.call_count == 2

    def test_right_button_sends_down_and_up(self, mock_user32) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(button=MouseButton.RIGHT), context=_connected())

        assert result.success is True
        assert mock_user32.SendInput.call_count == 2

    def test_middle_button_sends_down_and_up(self, mock_user32) -> None:
        backend = SendInputMouseBackend()
        result = backend.click(_click(button=MouseButton.MIDDLE), context=_connected())

        assert result.success is True
        assert mock_user32.SendInput.call_count == 2

    def test_get_button_flags_left(self) -> None:
        backend = SendInputMouseBackend()
        assert backend._get_button_flags(MouseButton.LEFT) == (
            MOUSEEVENTF_LEFTDOWN,
            MOUSEEVENTF_LEFTUP,
        )


class TestSendInputMouseBackendDuration:
    def test_duration_ms_sleeps(self, mock_user32, monkeypatch) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(
            "nzfz_executor.core.actions.backends.send_input_backend.time.sleep",
            lambda seconds: sleeps.append(seconds),
        )

        backend = SendInputMouseBackend()
        backend.click(_click(duration_ms=50), context=_connected())

        assert sleeps == [0.05]

    def test_zero_duration_no_sleep(self, mock_user32, monkeypatch) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(
            "nzfz_executor.core.actions.backends.send_input_backend.time.sleep",
            lambda seconds: sleeps.append(seconds),
        )

        backend = SendInputMouseBackend()
        backend.click(_click(duration_ms=0), context=_connected())

        assert sleeps == []

    def test_negative_duration_treated_as_zero(self, mock_user32, monkeypatch) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(
            "nzfz_executor.core.actions.backends.send_input_backend.time.sleep",
            lambda seconds: sleeps.append(seconds),
        )

        backend = SendInputMouseBackend()
        backend.click(_click(duration_ms=-10), context=_connected())

        assert sleeps == []


class TestSendInputMouseBackendDrag:
    def test_drag_outside_window_fails(self) -> None:
        backend = SendInputMouseBackend()
        result = backend.drag(
            MouseDragAction(
                start=ScreenPoint(x=50, y=50),
                end=ScreenPoint(x=150, y=50),
            ),
            context=_connected(),
        )

        assert result.success is False
        assert "超出连接窗口范围" in result.message

    def test_drag_releases_button_on_failure(self, mock_user32) -> None:
        mock_user32.SetCursorPos.side_effect = [1, 0]
        backend = SendInputMouseBackend()
        result = backend.drag(
            MouseDragAction(
                start=ScreenPoint(x=150, y=250),
                end=ScreenPoint(x=200, y=250),
            ),
            context=_connected(),
        )

        assert result.success is False
        assert mock_user32.SendInput.call_count >= 1

    def test_drag_success_moves_cursor(self, mock_user32, monkeypatch) -> None:
        monkeypatch.setattr(
            "nzfz_executor.core.actions.backends.send_input_backend.time.sleep",
            lambda _: None,
        )
        backend = SendInputMouseBackend()
        result = backend.drag(
            MouseDragAction(
                start=ScreenPoint(x=150, y=250),
                end=ScreenPoint(x=200, y=250),
                duration_ms=80,
            ),
            context=_connected(),
        )

        assert result.success is True
        assert mock_user32.SetCursorPos.call_count >= 5
        assert mock_user32.SendInput.call_count >= 2
