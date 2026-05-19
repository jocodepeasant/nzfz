from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from td_executor.engine.slot import (
    _micro_adjust_indices,
    get_micro_adjust_points,
    locate_slot,
    click_slot,
)
from td_executor.runtime.window import WindowRect


def _make_rect(left=0, top=0, width=1920, height=1080) -> WindowRect:
    return WindowRect(hwnd=1, left=left, top=top, width=width, height=height, title="test")


def _make_slots() -> list[dict]:
    return [
        {
            "slot_id": "A01",
            "name": "左入口减速位1",
            "region_id": "entrance_left",
            "position": {"x_ratio": 0.452, "y_ratio": 0.561},
            "precision": {
                "click_tolerance_px": 6,
                "allow_micro_adjust": True,
                "micro_adjust_pattern": "cross_5_points",
                "micro_adjust_step_px": 4,
            },
            "slot_type": "ground",
            "default_trap": "slow_trap",
            "verify": {
                "check_area": {"x_ratio": 0.435, "y_ratio": 0.545, "w_ratio": 0.035, "h_ratio": 0.035}
            },
        },
        {
            "slot_id": "A02",
            "name": "左入口输出位1",
            "region_id": "entrance_left",
            "position": {"x_ratio": 0.502, "y_ratio": 0.561},
            "precision": {
                "allow_micro_adjust": False,
            },
            "slot_type": "ground",
            "default_trap": "damage_trap",
            "verify": {},
        },
    ]


class TestLocateSlot:
    def test_found(self) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = locate_slot("A01", rect, slots)
        assert result["slot_id"] == "A01"
        assert result["region_id"] == "entrance_left"
        assert result["center_x"] == int(1920 * 0.452)
        assert result["center_y"] == int(1080 * 0.561)
        assert result["slot_type"] == "ground"
        assert result["default_trap"] == "slow_trap"
        assert "precision" in result
        assert "verify" in result

    def test_coordinate_conversion(self) -> None:
        rect = _make_rect(left=100, top=50, width=1920, height=1080)
        slots = [{"slot_id": "S1", "position": {"x_ratio": 0.5, "y_ratio": 0.5}, "region_id": "r1"}]
        result = locate_slot("S1", rect, slots)
        assert result["center_x"] == int(100 + 1920 * 0.5)
        assert result["center_y"] == int(50 + 1080 * 0.5)

    def test_not_found(self) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = locate_slot("X99", rect, slots)
        assert result == {}

    def test_empty_slots(self) -> None:
        rect = _make_rect()
        result = locate_slot("A01", rect, [])
        assert result == {}

    def test_second_slot(self) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = locate_slot("A02", rect, slots)
        assert result["slot_id"] == "A02"
        assert result["center_x"] == int(1920 * 0.502)

    def test_missing_position_defaults_to_zero(self) -> None:
        rect = _make_rect(left=0, top=0, width=1920, height=1080)
        slots = [{"slot_id": "S1", "region_id": "r1"}]
        result = locate_slot("S1", rect, slots)
        assert result["center_x"] == 0
        assert result["center_y"] == 0


class TestGetMicroAdjustPoints:
    def test_cross_5_points(self) -> None:
        precision = {
            "allow_micro_adjust": True,
            "micro_adjust_pattern": "cross_5_points",
            "micro_adjust_step_px": 4,
        }
        points = get_micro_adjust_points(867, 605, precision)
        assert points == [(867, 605), (867, 601), (867, 609), (863, 605), (871, 605)]

    def test_cross_5_points_default_step(self) -> None:
        precision = {
            "allow_micro_adjust": True,
            "micro_adjust_pattern": "cross_5_points",
        }
        points = get_micro_adjust_points(100, 200, precision)
        assert points == [(100, 200), (100, 196), (100, 204), (96, 200), (104, 200)]

    def test_not_allowed(self) -> None:
        precision = {"allow_micro_adjust": False}
        points = get_micro_adjust_points(867, 605, precision)
        assert points == []

    def test_empty_precision(self) -> None:
        points = get_micro_adjust_points(867, 605, {})
        assert points == []

    def test_none_precision(self) -> None:
        points = get_micro_adjust_points(867, 605, None)
        assert points == []

    def test_unknown_pattern(self) -> None:
        precision = {
            "allow_micro_adjust": True,
            "micro_adjust_pattern": "grid_9_points",
        }
        points = get_micro_adjust_points(867, 605, precision)
        assert points == []

    def test_missing_allow_key(self) -> None:
        precision = {"micro_adjust_pattern": "cross_5_points"}
        points = get_micro_adjust_points(867, 605, precision)
        assert points == []


class TestClickSlot:
    def setup_method(self) -> None:
        _micro_adjust_indices.clear()

    @patch("td_executor.engine.slot.click_at")
    def test_normal_mode(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = click_slot("A01", rect, slots, micro_adjust=False)
        assert result is True
        expected_x = int(1920 * 0.452)
        expected_y = int(1080 * 0.561)
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    @patch("td_executor.engine.slot.click_at")
    def test_micro_adjust_first_call(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = click_slot("A01", rect, slots, micro_adjust=True)
        assert result is True
        expected_x = int(1920 * 0.452)
        expected_y = int(1080 * 0.561)
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    @patch("td_executor.engine.slot.click_at")
    def test_micro_adjust_second_call(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        click_slot("A01", rect, slots, micro_adjust=True)
        mock_click.reset_mock()
        result = click_slot("A01", rect, slots, micro_adjust=True)
        assert result is True
        expected_x = int(1920 * 0.452)
        expected_y = int(1080 * 0.561) - 4
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    @patch("td_executor.engine.slot.click_at")
    def test_micro_adjust_index_cycles(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        for _ in range(5):
            click_slot("A01", rect, slots, micro_adjust=True)
        mock_click.reset_mock()
        result = click_slot("A01", rect, slots, micro_adjust=True)
        assert result is True
        expected_x = int(1920 * 0.452)
        expected_y = int(1080 * 0.561)
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    @patch("td_executor.engine.slot.click_at")
    def test_micro_adjust_different_slots(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        click_slot("A01", rect, slots, micro_adjust=True)
        mock_click.reset_mock()
        result = click_slot("A02", rect, slots, micro_adjust=True)
        assert result is True
        expected_x = int(1920 * 0.502)
        expected_y = int(1080 * 0.561)
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    def test_slot_not_found(self) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = click_slot("X99", rect, slots)
        assert result is False

    @patch("td_executor.engine.slot.click_at", side_effect=RuntimeError("pyautogui unavailable"))
    def test_click_at_exception(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = click_slot("A01", rect, slots)
        assert result is False

    @patch("td_executor.engine.slot.click_at")
    def test_micro_adjust_no_points_fallback(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        result = click_slot("A02", rect, slots, micro_adjust=True)
        assert result is True
        expected_x = int(1920 * 0.502)
        expected_y = int(1080 * 0.561)
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)

    @patch("td_executor.engine.slot.click_at")
    def test_normal_mode_does_not_affect_index(self, mock_click: MagicMock) -> None:
        rect = _make_rect()
        slots = _make_slots()
        click_slot("A01", rect, slots, micro_adjust=True)
        click_slot("A01", rect, slots, micro_adjust=False)
        mock_click.reset_mock()
        click_slot("A01", rect, slots, micro_adjust=True)
        expected_x = int(1920 * 0.452)
        expected_y = int(1080 * 0.561) - 4
        mock_click.assert_called_once_with(expected_x, expected_y, overlay=None)


class TestEngineExports:
    def test_import_from_engine(self) -> None:
        from td_executor.engine import locate_slot, get_micro_adjust_points, click_slot
        assert callable(locate_slot)
        assert callable(get_micro_adjust_points)
        assert callable(click_slot)
