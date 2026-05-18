from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from td_executor.engine.action import (
    _PYNPUT_AVAILABLE,
    _PYAUTOGUI_AVAILABLE,
    _KNOWN_ACTION_TYPES,
    _SPECIAL_KEY_MAP,
    MAP_OPEN_WAIT_MS,
    MAP_OPEN_MAX_RETRIES,
    click_at,
    drag,
    ensure_map_open,
    execute_action,
    press_key,
)


class TestPressKey:
    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController")
    def test_short_press(self, mock_controller_cls: MagicMock) -> None:
        mock_kb = MagicMock()
        mock_controller_cls.return_value = mock_kb
        press_key("o")
        mock_kb.press.assert_called_once_with("o")
        mock_kb.release.assert_called_once_with("o")

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController")
    @patch("td_executor.engine.action.time.sleep")
    def test_long_press(self, mock_sleep: MagicMock, mock_controller_cls: MagicMock) -> None:
        mock_kb = MagicMock()
        mock_controller_cls.return_value = mock_kb
        press_key("2", hold_ms=4000)
        mock_kb.press.assert_called_once_with("2")
        mock_sleep.assert_called_once_with(4.0)
        mock_kb.release.assert_called_once_with("2")

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController")
    def test_special_key_enter(self, mock_controller_cls: MagicMock) -> None:
        mock_kb = MagicMock()
        mock_controller_cls.return_value = mock_kb
        if "enter" in _SPECIAL_KEY_MAP:
            press_key("enter")
            mock_kb.press.assert_called_once()
            mock_kb.release.assert_called_once()
            resolved = mock_kb.press.call_args[0][0]
            assert resolved == _SPECIAL_KEY_MAP["enter"]
        else:
            press_key("enter")
            mock_kb.press.assert_called_once_with("enter")
            mock_kb.release.assert_called_once_with("enter")

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController")
    def test_special_key_space(self, mock_controller_cls: MagicMock) -> None:
        mock_kb = MagicMock()
        mock_controller_cls.return_value = mock_kb
        if "space" in _SPECIAL_KEY_MAP:
            press_key("space")
            resolved = mock_kb.press.call_args[0][0]
            assert resolved == _SPECIAL_KEY_MAP["space"]
        else:
            press_key("space")
            mock_kb.press.assert_called_once_with("space")

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController")
    @patch("td_executor.engine.action.time.sleep")
    def test_hold_ms_zero_no_sleep(self, mock_sleep: MagicMock, mock_controller_cls: MagicMock) -> None:
        mock_kb = MagicMock()
        mock_controller_cls.return_value = mock_kb
        press_key("a", hold_ms=0)
        mock_sleep.assert_not_called()

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", False)
    def test_pynput_unavailable(self) -> None:
        with pytest.raises(RuntimeError, match="pynput is not available"):
            press_key("o")

    @patch("td_executor.engine.action._PYNPUT_AVAILABLE", True)
    @patch("td_executor.engine.action.KeyboardController", None)
    def test_pynput_controller_none(self) -> None:
        with pytest.raises(RuntimeError, match="pynput is not available"):
            press_key("o")


class TestClickAt:
    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui")
    def test_left_click(self, mock_pyautogui: MagicMock) -> None:
        click_at(960, 540)
        mock_pyautogui.click.assert_called_once_with(x=960, y=540, button="left")

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui")
    def test_right_click(self, mock_pyautogui: MagicMock) -> None:
        click_at(960, 540, button="right")
        mock_pyautogui.click.assert_called_once_with(x=960, y=540, button="right")

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", False)
    def test_pyautogui_unavailable(self) -> None:
        with pytest.raises(RuntimeError, match="pyautogui is not available"):
            click_at(960, 540)

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui", None)
    def test_pyautogui_none(self) -> None:
        with pytest.raises(RuntimeError, match="pyautogui is not available"):
            click_at(960, 540)


class TestDrag:
    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui")
    def test_default_duration(self, mock_pyautogui: MagicMock) -> None:
        drag(100, 200, 300, 400)
        mock_pyautogui.moveTo.assert_any_call(100, 200, duration=0.0)
        mock_pyautogui.mouseDown.assert_called_once_with(button="left")
        mock_pyautogui.moveTo.assert_any_call(300, 400, duration=0.6)
        mock_pyautogui.mouseUp.assert_called_once_with(button="left")

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui")
    def test_custom_duration(self, mock_pyautogui: MagicMock) -> None:
        drag(100, 200, 300, 400, duration_ms=1000)
        mock_pyautogui.moveTo.assert_any_call(300, 400, duration=1.0)

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", True)
    @patch("td_executor.engine.action.pyautogui")
    def test_drag_sequence(self, mock_pyautogui: MagicMock) -> None:
        drag(50, 60, 70, 80, duration_ms=500)
        calls = mock_pyautogui.method_calls
        assert calls[0] == call.moveTo(50, 60, duration=0.0)
        assert calls[1] == call.mouseDown(button="left")
        assert calls[2] == call.moveTo(70, 80, duration=0.5)
        assert calls[3] == call.mouseUp(button="left")

    @patch("td_executor.engine.action._PYAUTOGUI_AVAILABLE", False)
    def test_pyautogui_unavailable(self) -> None:
        with pytest.raises(RuntimeError, match="pyautogui is not available"):
            drag(100, 200, 300, 400)


class TestEnsureMapOpen:
    @patch("td_executor.vision.detector.VisionDetector")
    def test_map_already_open(self, mock_detector_cls: MagicMock) -> None:
        mock_detector = MagicMock()
        mock_detector.is_map_ui_open.return_value = True
        mock_detector_cls.return_value = mock_detector
        result = ensure_map_open(MagicMock(), MagicMock(), {})
        assert result is True
        mock_detector.is_map_ui_open.assert_called_once()

    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.vision.detector.VisionDetector")
    def test_map_opens_after_one_press(self, mock_detector_cls: MagicMock, mock_sleep: MagicMock, mock_press: MagicMock) -> None:
        mock_detector = MagicMock()
        mock_detector.is_map_ui_open.side_effect = [False, True]
        mock_detector_cls.return_value = mock_detector
        result = ensure_map_open(MagicMock(), MagicMock(), {})
        assert result is True
        mock_press.assert_called_once_with("o")

    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.vision.detector.VisionDetector")
    def test_map_opens_after_multiple_retries(self, mock_detector_cls: MagicMock, mock_sleep: MagicMock, mock_press: MagicMock) -> None:
        mock_detector = MagicMock()
        mock_detector.is_map_ui_open.side_effect = [False, False, False, True]
        mock_detector_cls.return_value = mock_detector
        result = ensure_map_open(MagicMock(), MagicMock(), {})
        assert result is True
        assert mock_press.call_count == 3

    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.vision.detector.VisionDetector")
    def test_map_never_opens(self, mock_detector_cls: MagicMock, mock_sleep: MagicMock, mock_press: MagicMock) -> None:
        mock_detector = MagicMock()
        mock_detector.is_map_ui_open.return_value = False
        mock_detector_cls.return_value = mock_detector
        result = ensure_map_open(MagicMock(), MagicMock(), {})
        assert result is False
        assert mock_press.call_count == MAP_OPEN_MAX_RETRIES

    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.vision.detector.VisionDetector")
    def test_wait_between_retries(self, mock_detector_cls: MagicMock, mock_sleep: MagicMock, mock_press: MagicMock) -> None:
        mock_detector = MagicMock()
        mock_detector.is_map_ui_open.side_effect = [False, False, True]
        mock_detector_cls.return_value = mock_detector
        ensure_map_open(MagicMock(), MagicMock(), {})
        sleep_calls = [c for c in mock_sleep.call_args_list]
        assert len(sleep_calls) == 2
        for c in sleep_calls:
            assert c[0][0] == MAP_OPEN_WAIT_MS / 1000.0


class TestExecuteAction:
    def test_log_action(self) -> None:
        result = execute_action({"type": "log", "message": "第1波布防完成"}, {})
        assert result == {"success": True, "skipped": False}

    def test_log_action_empty_message(self) -> None:
        result = execute_action({"type": "log"}, {})
        assert result == {"success": True, "skipped": False}

    def test_place_trap_map_not_open(self) -> None:
        result = execute_action({"type": "place_trap", "trap_id": "slow_trap", "slot_id": "A01", "conditions": {}, "on_condition_failed": {"policy": "skip"}, "verify": {}, "retry": {}, "on_fail": {"policy": "skip"}}, {})
        assert result["success"] is False

    def test_upgrade_trap_map_not_open(self) -> None:
        result = execute_action({"type": "upgrade_trap", "trap_id": "slow_trap", "target_level": 2, "conditions": {}, "on_condition_failed": {"policy": "skip"}, "execute": {}, "verify": {}, "retry": {}, "on_fail": {"policy": "skip"}}, {})
        assert result["success"] is False

    def test_remove_trap_map_not_open(self) -> None:
        result = execute_action({"type": "remove_trap", "slot_id": "A01", "conditions": {}, "on_condition_failed": {"policy": "skip"}, "execute": {}, "verify": {}, "retry": {}, "on_fail": {"policy": "skip"}}, {})
        assert result["success"] is False

    def test_pan_to_region_failure(self) -> None:
        result = execute_action({"type": "pan_to_region", "region_id": "test", "retry": {"max_count": 0}, "on_fail": {"policy": "skip"}}, {})
        assert result["success"] is False

    def test_unknown_action_type(self) -> None:
        result = execute_action({"type": "unknown"}, {})
        assert result["success"] is False
        assert result["skipped"] is False
        assert "unknown action type: unknown" == result["error"]

    def test_empty_type(self) -> None:
        result = execute_action({}, {})
        assert result["success"] is False
        assert "unknown action type: " in result["error"]


class TestConstants:
    def test_known_action_types(self) -> None:
        assert "place_trap" in _KNOWN_ACTION_TYPES
        assert "upgrade_trap" in _KNOWN_ACTION_TYPES
        assert "remove_trap" in _KNOWN_ACTION_TYPES
        assert "pan_to_region" in _KNOWN_ACTION_TYPES
        assert "log" in _KNOWN_ACTION_TYPES

    def test_map_open_constants(self) -> None:
        assert MAP_OPEN_WAIT_MS == 800
        assert MAP_OPEN_MAX_RETRIES == 3


class TestEngineExports:
    def test_import_from_engine(self) -> None:
        from td_executor.engine import press_key, click_at, drag, ensure_map_open, execute_action
        assert callable(press_key)
        assert callable(click_at)
        assert callable(drag)
        assert callable(ensure_map_open)
        assert callable(execute_action)
