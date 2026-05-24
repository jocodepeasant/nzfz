"""P2-11 SendInputKeyboardBackend 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nzfz_executor.core.actions.backends.send_input_keyboard_backend import (
    SendInputKeyboardBackend,
)


@pytest.fixture
def mock_user32():
    with patch(
        "nzfz_executor.core.actions.backends.send_input_keyboard_backend.ctypes.windll",
    ) as windll:
        user32 = MagicMock()
        windll.user32 = user32
        user32.SendInput.return_value = 1
        yield user32


class TestSendInputKeyboardBackend:
    def test_press_sends_down_and_up(self, mock_user32) -> None:
        backend = SendInputKeyboardBackend()
        backend.press("1", hold_ms=0)

        assert mock_user32.SendInput.call_count == 2

    def test_hold_ms_sleeps(self, mock_user32, monkeypatch) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(
            "nzfz_executor.core.actions.backends.send_input_keyboard_backend.time.sleep",
            lambda seconds: sleeps.append(seconds),
        )

        backend = SendInputKeyboardBackend()
        backend.press("o", hold_ms=100)

        assert sleeps == [0.1]
        assert mock_user32.SendInput.call_count == 2

    def test_unsupported_key_raises(self) -> None:
        backend = SendInputKeyboardBackend()
        with pytest.raises(ValueError, match="不支持的按键"):
            backend.press("f1")

    def test_key_up_is_second_send_input_call(self, mock_user32) -> None:
        backend = SendInputKeyboardBackend()
        backend.press("enter")

        assert mock_user32.SendInput.call_count == 2
