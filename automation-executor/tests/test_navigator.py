from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from td_executor.engine.navigator import (
    NavigatorConfig,
    calculate_pan_endpoints,
    go_to_origin,
    execute_pan_action,
    pan_to_region,
    _find_region,
)
from td_executor.runtime.window import WindowRect

TEST_RECT = WindowRect(hwnd=1, left=0, top=0, width=1920, height=1080)


class TestNavigatorConfig:
    def test_default_values(self) -> None:
        cfg = NavigatorConfig()
        assert cfg.map_close_wait_ms == 500
        assert cfg.map_open_wait_ms == 800
        assert cfg.wait_after_pan_ms == 800

    def test_custom_values(self) -> None:
        cfg = NavigatorConfig(map_close_wait_ms=200, map_open_wait_ms=300, wait_after_pan_ms=400)
        assert cfg.map_close_wait_ms == 200
        assert cfg.map_open_wait_ms == 300
        assert cfg.wait_after_pan_ms == 400


class TestCalculatePanEndpoints:
    @pytest.mark.parametrize(
        "direction, ratio, expected_end",
        [
            ("left", 0.5, (960, 540 - 0, 960 - 960, 540)),
            ("right", 0.5, (960, 540, 960 + 960, 540)),
            ("up", 0.5, (960, 540, 960, 540 - 540)),
            ("down", 0.5, (960, 540, 960, 540 + 540)),
            ("left", 0.25, (960, 540, 960 - 480, 540)),
            ("right", 0.25, (960, 540, 960 + 480, 540)),
            ("up", 0.25, (960, 540, 960, 540 - 270)),
            ("down", 0.25, (960, 540, 960, 540 + 270)),
        ],
    )
    def test_known_directions(self, direction: str, ratio: float, expected_end: tuple) -> None:
        result = calculate_pan_endpoints(TEST_RECT, direction, ratio)
        assert result is not None
        (sx, sy), (ex, ey) = result
        assert (sx, sy) == (expected_end[0], expected_end[1])
        assert (ex, ey) == (expected_end[2], expected_end[3])

    def test_left_direction_exact(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "left", 0.5)
        assert result == ((960, 540), (0, 540))

    def test_right_direction_exact(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "right", 0.5)
        assert result == ((960, 540), (1920, 540))

    def test_up_direction_exact(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "up", 0.5)
        assert result == ((960, 540), (960, 0))

    def test_down_direction_exact(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "down", 0.5)
        assert result == ((960, 540), (960, 1080))

    def test_unknown_direction_returns_none(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "diagonal", 0.5)
        assert result is None

    def test_zero_ratio(self) -> None:
        result = calculate_pan_endpoints(TEST_RECT, "left", 0)
        assert result is not None
        (sx, sy), (ex, ey) = result
        assert (sx, sy) == (ex, ey)

    def test_non_zero_offset_rect(self) -> None:
        rect = WindowRect(hwnd=2, left=100, top=50, width=800, height=600)
        result = calculate_pan_endpoints(rect, "right", 0.5)
        assert result is not None
        (sx, sy), (ex, ey) = result
        assert sx == 100 + 800 // 2
        assert sy == 50 + 600 // 2
        assert ex == sx + 400
        assert ey == sy


class TestGoToOrigin:
    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_map_already_open(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [True, True]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is True
        assert mock_ensure.call_count == 2
        assert mock_press.call_count == 2
        mock_press.assert_any_call("o")
        assert mock_sleep.call_count == 2

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_map_not_open(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [False, True]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is True
        assert mock_ensure.call_count == 2
        mock_press.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_map_not_open_ensure_fails(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.return_value = False
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is False
        mock_press.assert_not_called()

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_press_key_raises_runtime_error_on_close(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.return_value = True
        mock_press.side_effect = RuntimeError("unavailable")
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is False

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_press_key_raises_runtime_error_on_reopen(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [True, True]
        call_count = 0

        def _press(key: str) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("unavailable")

        mock_press.side_effect = _press
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is False

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_ensure_map_open_false_after_reopen(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [True, False]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is False
        assert mock_press.call_count == 2

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_config_none_creates_from_runtime(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [True, True]
        capture = MagicMock()
        rois = {}
        runtime = {"wait_after_pan_ms": 1200}
        result = go_to_origin(capture, TEST_RECT, rois, runtime)
        assert result is True
        close_sleep = mock_sleep.call_args_list[0]
        assert close_sleep[0][0] == 500 / 1000.0
        open_sleep = mock_sleep.call_args_list[1]
        assert open_sleep[0][0] == 800 / 1000.0

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.press_key")
    @patch("td_executor.engine.navigator.ensure_map_open")
    def test_custom_config_wait_times(self, mock_ensure: MagicMock, mock_press: MagicMock, mock_sleep: MagicMock) -> None:
        mock_ensure.side_effect = [True, True]
        capture = MagicMock()
        rois = {}
        runtime = {}
        config = NavigatorConfig(map_close_wait_ms=200, map_open_wait_ms=300, wait_after_pan_ms=400)
        result = go_to_origin(capture, TEST_RECT, rois, runtime, config)
        assert result is True
        close_sleep = mock_sleep.call_args_list[0]
        assert close_sleep[0][0] == 200 / 1000.0
        open_sleep = mock_sleep.call_args_list[1]
        assert open_sleep[0][0] == 300 / 1000.0


class TestExecutePanAction:
    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_single_drag(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        action = {"direction": "left", "distance_ratio": 0.5, "duration_ms": 600, "repeat": 1}
        result = execute_pan_action(action, TEST_RECT)
        assert result is True
        mock_drag.assert_called_once_with(960, 540, 0, 540, 600)
        mock_sleep.assert_called_once_with(800 / 1000.0)

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_repeat_three(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        action = {"direction": "right", "distance_ratio": 0.25, "duration_ms": 500, "repeat": 3}
        result = execute_pan_action(action, TEST_RECT)
        assert result is True
        assert mock_drag.call_count == 3
        assert mock_sleep.call_count == 3

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_drag_raises_runtime_error(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        mock_drag.side_effect = RuntimeError("unavailable")
        action = {"direction": "left", "distance_ratio": 0.5, "repeat": 1}
        result = execute_pan_action(action, TEST_RECT)
        assert result is False

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_unknown_direction(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        action = {"direction": "diagonal", "distance_ratio": 0.5}
        result = execute_pan_action(action, TEST_RECT)
        assert result is False
        mock_drag.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_default_values_for_missing_fields(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        action = {"direction": "down"}
        result = execute_pan_action(action, TEST_RECT)
        assert result is True
        mock_drag.assert_called_once_with(960, 540, 960, 540, 600)

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_custom_config_wait_after_pan(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        action = {"direction": "up", "distance_ratio": 0.5, "repeat": 1}
        config = NavigatorConfig(wait_after_pan_ms=400)
        result = execute_pan_action(action, TEST_RECT, config)
        assert result is True
        mock_sleep.assert_called_once_with(400 / 1000.0)

    @patch("td_executor.engine.navigator.time.sleep")
    @patch("td_executor.engine.navigator.drag")
    def test_drag_stops_on_runtime_error_mid_repeat(self, mock_drag: MagicMock, mock_sleep: MagicMock) -> None:
        call_count = 0

        def _drag(fx: int, fy: int, tx: int, ty: int, dur: int) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("unavailable")

        mock_drag.side_effect = _drag
        action = {"direction": "left", "distance_ratio": 0.5, "repeat": 3}
        result = execute_pan_action(action, TEST_RECT)
        assert result is False
        assert mock_drag.call_count == 2


class TestFindRegion:
    def test_finds_region(self) -> None:
        regions = [
            {"region_id": "r1", "enter_actions": []},
            {"region_id": "r2", "enter_actions": [{"type": "pan_map", "direction": "left"}]},
        ]
        result = _find_region(regions, "r2")
        assert result is not None
        assert result["region_id"] == "r2"

    def test_not_found(self) -> None:
        regions = [
            {"region_id": "r1", "enter_actions": []},
        ]
        result = _find_region(regions, "r_missing")
        assert result is None

    def test_empty_list(self) -> None:
        result = _find_region([], "r1")
        assert result is None

    def test_region_without_id_field(self) -> None:
        regions = [{"name": "no_id"}]
        result = _find_region(regions, "r1")
        assert result is None


class TestPanToRegion:
    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_normal_flow(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        mock_exec.return_value = True
        regions = [
            {"region_id": "target", "enter_actions": [
                {"type": "pan_map", "direction": "left", "distance_ratio": 0.5},
                {"type": "pan_map", "direction": "up", "distance_ratio": 0.3},
            ]},
        ]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("target", TEST_RECT, regions, capture, rois, runtime)
        assert result is True
        mock_origin.assert_called_once()
        assert mock_exec.call_count == 2

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_region_not_found(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        regions = [{"region_id": "other", "enter_actions": []}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("missing", TEST_RECT, regions, capture, rois, runtime)
        assert result is False
        mock_exec.assert_not_called()

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_origin_region_empty_enter_actions(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        regions = [{"region_id": "origin", "enter_actions": []}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("origin", TEST_RECT, regions, capture, rois, runtime)
        assert result is True
        mock_exec.assert_not_called()

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_go_to_origin_fails(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = False
        regions = [{"region_id": "target", "enter_actions": [{"type": "pan_map", "direction": "left"}]}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("target", TEST_RECT, regions, capture, rois, runtime)
        assert result is False
        mock_exec.assert_not_called()

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_execute_pan_action_fails_mid_sequence(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        mock_exec.side_effect = [True, False]
        regions = [{"region_id": "target", "enter_actions": [
            {"type": "pan_map", "direction": "left"},
            {"type": "pan_map", "direction": "up"},
        ]}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("target", TEST_RECT, regions, capture, rois, runtime)
        assert result is False
        assert mock_exec.call_count == 2

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_skips_non_pan_map_actions(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        mock_exec.return_value = True
        regions = [{"region_id": "target", "enter_actions": [
            {"type": "other_action"},
            {"type": "pan_map", "direction": "left", "distance_ratio": 0.5},
        ]}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("target", TEST_RECT, regions, capture, rois, runtime)
        assert result is True
        assert mock_exec.call_count == 1

    @patch("td_executor.engine.navigator.execute_pan_action")
    @patch("td_executor.engine.navigator.go_to_origin")
    def test_config_passed_through(self, mock_origin: MagicMock, mock_exec: MagicMock) -> None:
        mock_origin.return_value = True
        mock_exec.return_value = True
        config = NavigatorConfig(wait_after_pan_ms=200)
        regions = [{"region_id": "target", "enter_actions": [
            {"type": "pan_map", "direction": "left", "distance_ratio": 0.5},
        ]}]
        capture = MagicMock()
        rois = {}
        runtime = {}
        result = pan_to_region("target", TEST_RECT, regions, capture, rois, runtime, config)
        assert result is True
        mock_origin.assert_called_once_with(capture, TEST_RECT, rois, runtime, config)
        mock_exec.assert_called_once()
        assert mock_exec.call_args[0][0] == {"type": "pan_map", "direction": "left", "distance_ratio": 0.5}
        assert mock_exec.call_args[0][1] == TEST_RECT
        assert mock_exec.call_args[0][2] == config
