from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from td_executor.runtime.input import MAKELPARAM, send_click, send_key


class TestMAKELPARAM:
    def test_packs_lo_and_hi(self) -> None:
        result = MAKELPARAM(100, 200)
        assert result == (100 & 0xFFFF) | ((200 & 0xFFFF) << 16)

    def test_zero_values(self) -> None:
        assert MAKELPARAM(0, 0) == 0

    def test_lo_only(self) -> None:
        assert MAKELPARAM(500, 0) == 500

    def test_hi_only(self) -> None:
        assert MAKELPARAM(0, 500) == 500 << 16

    def test_masks_overflow(self) -> None:
        result = MAKELPARAM(0x1FFFF, 0x1FFFF)
        assert result == 0xFFFF | (0xFFFF << 16)


class TestSendClick:
    def test_fallback_pyautogui_left(self) -> None:
        mock_pyautogui = MagicMock()
        with patch.dict(sys.modules, {"pyautogui": mock_pyautogui}):
            send_click(0, 100, 200)
            mock_pyautogui.click.assert_called_once_with(x=100, y=200, button="left")

    def test_fallback_pyautogui_right(self) -> None:
        mock_pyautogui = MagicMock()
        with patch.dict(sys.modules, {"pyautogui": mock_pyautogui}):
            send_click(0, 300, 400, button="right")
            mock_pyautogui.click.assert_called_once_with(x=300, y=400, button="right")

    def test_pyautogui_not_available(self) -> None:
        with patch.dict(sys.modules, {"pyautogui": None}), \
             patch("td_executor.runtime.input.logger") as mock_logger:
            send_click(0, 100, 200)
            mock_logger.warning.assert_called_once()


class TestSendKey:
    def test_fallback_pynput(self) -> None:
        mock_controller = MagicMock()
        mock_keyboard = MagicMock()
        mock_keyboard.Controller = mock_controller
        mock_keyboard.Key = MagicMock()
        mock_pynput = MagicMock()
        mock_pynput.keyboard = mock_keyboard
        with patch.dict(sys.modules, {"pynput": mock_pynput, "pynput.keyboard": mock_keyboard}):
            send_key(0, "a")
            mock_controller.return_value.press.assert_called_once_with("a")
            mock_controller.return_value.release.assert_called_once_with("a")

    def test_fallback_pynput_with_hold_ms(self) -> None:
        mock_controller = MagicMock()
        mock_keyboard = MagicMock()
        mock_keyboard.Controller = mock_controller
        mock_keyboard.Key = MagicMock()
        mock_pynput = MagicMock()
        mock_pynput.keyboard = mock_keyboard
        with patch.dict(sys.modules, {"pynput": mock_pynput, "pynput.keyboard": mock_keyboard}), \
             patch("td_executor.runtime.input.time.sleep") as mock_sleep:
            send_key(0, "a", hold_ms=500)
            mock_controller.return_value.press.assert_called_once_with("a")
            mock_controller.return_value.release.assert_called_once_with("a")
            mock_sleep.assert_called_once_with(0.5)

    def test_pynput_not_available(self) -> None:
        with patch.dict(sys.modules, {"pynput": None, "pynput.keyboard": None}), \
             patch("td_executor.runtime.input.logger") as mock_logger:
            send_key(0, "a")
            mock_logger.warning.assert_called_once()
