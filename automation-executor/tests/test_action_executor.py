from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from td_executor.engine.action import ActionExecutor, execute_action
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
            "precision": {"allow_micro_adjust": True, "micro_adjust_pattern": "cross_5_points", "micro_adjust_step_px": 4},
            "slot_type": "ground",
            "default_trap": "slow_trap",
            "verify": {"check_area": {"x_ratio": 0.435, "y_ratio": 0.545, "w_ratio": 0.035, "h_ratio": 0.035}},
        },
    ]


def _make_traps() -> list[dict]:
    return [
        {
            "trap_id": "slow_trap",
            "trap_name": "减速陷阱",
            "select_key": "1",
            "upgrade_key": "1",
            "upgrade_hold_ms": 4000,
            "cost": 500,
            "upgrade_cost": 1000,
            "max_level": 3,
        },
        {
            "trap_id": "damage_trap",
            "trap_name": "输出陷阱",
            "select_key": "2",
            "upgrade_key": "2",
            "upgrade_hold_ms": 4000,
            "cost": 800,
            "upgrade_cost": 1500,
            "max_level": 3,
        },
    ]


def _make_regions() -> list[dict]:
    return [
        {
            "region_id": "entrance_left",
            "name": "左入口",
            "enter_actions": [
                {"type": "pan_map", "direction": "left", "distance_ratio": 0.3, "duration_ms": 600}
            ],
        },
    ]


def _make_context(**overrides) -> dict:
    ctx = {
        "capture": MagicMock(),
        "rect": _make_rect(),
        "rois": {"map_ui_indicator": {}},
        "slots": _make_slots(),
        "traps": _make_traps(),
        "regions": _make_regions(),
        "runtime": {"wait_after_place_ms": 600, "wait_after_upgrade_ms": 1000, "wait_after_remove_ms": 600},
        "state": {"trap_levels": {}},
        "multi_frame": None,
        "wave": 1,
    }
    ctx.update(overrides)
    return ctx


class TestActionExecutorInit:
    def test_creates_instances(self) -> None:
        executor = ActionExecutor()
        assert executor._retry_manager is not None
        assert executor._detector is not None
        assert executor._condition_engine is not None

    def test_custom_detector(self) -> None:
        detector = MagicMock()
        executor = ActionExecutor(detector=detector)
        assert executor._detector is detector

    def test_runtime_defaults(self) -> None:
        executor = ActionExecutor(runtime_defaults={"default_retry_count": 5})
        assert executor._retry_manager is not None


class TestExecuteDispatch:
    def setup_method(self) -> None:
        self.executor = ActionExecutor()

    def test_log_action(self) -> None:
        result = self.executor.execute({"type": "log", "message": "test"}, {})
        assert result["success"] is True
        assert result["skipped"] is False

    def test_unknown_type(self) -> None:
        result = self.executor.execute({"type": "unknown"}, {})
        assert result["success"] is False
        assert "unknown action type" in result["error"]


class TestExecutePlaceTrap:
    def setup_method(self) -> None:
        self.detector = MagicMock()
        self.executor = ActionExecutor(detector=self.detector)

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.slot.click_slot", return_value=True)
    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot")
    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_success(self, mock_pan, mock_locate, mock_map, mock_press, mock_click, mock_sleep) -> None:
        mock_locate.return_value = {"slot_id": "A01", "region_id": "entrance_left", "center_x": 867, "center_y": 605, "precision": {}, "verify": {}, "slot_type": "ground", "default_trap": "slow_trap"}
        self.detector.is_slot_occupied.return_value = True
        ctx = _make_context()
        action = {
            "type": "place_trap",
            "trap_id": "slow_trap",
            "slot_id": "A01",
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "verify": {"type": "slot_has_trap", "slot_id": "A01", "required": True},
            "retry": {"max_count": 0},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        mock_press.assert_called_with("1", overlay=None)
        mock_click.assert_called_with("A01", ctx["rect"], ctx["slots"], overlay=None)

    @patch("td_executor.engine.action.ensure_map_open", return_value=False)
    def test_map_not_open(self, mock_map) -> None:
        ctx = _make_context()
        action = {"type": "place_trap", "trap_id": "slow_trap", "slot_id": "A01", "conditions": {}, "on_condition_failed": {"policy": "skip"}, "verify": {}, "retry": {}, "on_fail": {"policy": "skip"}}
        result = self.executor.execute(action, ctx)
        assert result["success"] is False
        assert "map not open" in result["error"]

    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot", return_value={})
    def test_slot_not_found(self, mock_locate, mock_map) -> None:
        ctx = _make_context()
        action = {"type": "place_trap", "trap_id": "slow_trap", "slot_id": "X99", "conditions": {}, "on_condition_failed": {"policy": "skip"}, "verify": {}, "retry": {}, "on_fail": {"policy": "skip"}}
        result = self.executor.execute(action, ctx)
        assert result["success"] is False
        assert "slot not found" in result["error"]

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.slot.click_slot", return_value=True)
    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot")
    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_condition_skip(self, mock_pan, mock_locate, mock_map, mock_press, mock_click, mock_sleep) -> None:
        mock_locate.return_value = {"slot_id": "A01", "region_id": "entrance_left", "center_x": 867, "center_y": 605, "precision": {}, "verify": {}, "slot_type": "ground", "default_trap": "slow_trap"}
        ctx = _make_context()
        action = {
            "type": "place_trap",
            "trap_id": "slow_trap",
            "slot_id": "A01",
            "conditions": {"resource_gte": 99999},
            "on_condition_failed": {"policy": "skip"},
            "verify": {},
            "retry": {},
            "on_fail": {"policy": "skip"},
        }
        with patch.object(self.executor._condition_engine, "eval_conditions", return_value=False):
            result = self.executor.execute(action, ctx)
        assert result["skipped"] is True

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.slot.click_slot", return_value=True)
    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot")
    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_state_updated_on_success(self, mock_pan, mock_locate, mock_map, mock_press, mock_click, mock_sleep) -> None:
        mock_locate.return_value = {"slot_id": "A01", "region_id": "entrance_left", "center_x": 867, "center_y": 605, "precision": {}, "verify": {}, "slot_type": "ground", "default_trap": "slow_trap"}
        self.detector.is_slot_occupied.return_value = True
        ctx = _make_context()
        action = {
            "type": "place_trap",
            "trap_id": "slow_trap",
            "slot_id": "A01",
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "verify": {"type": "slot_has_trap", "slot_id": "A01", "required": True},
            "retry": {"max_count": 0},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        assert ctx["state"]["trap_levels"]["slow_trap"] == 1


class TestExecuteUpgradeTrap:
    def setup_method(self) -> None:
        self.detector = MagicMock()
        self.executor = ActionExecutor(detector=self.detector)

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    def test_success_with_execute_params(self, mock_map, mock_press, mock_sleep) -> None:
        ctx = _make_context()
        action = {
            "type": "upgrade_trap",
            "trap_id": "damage_trap",
            "target_level": 2,
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "execute": {"method": "hold_key", "key": "2", "hold_ms": 4000},
            "verify": {"type": "trap_level_gte", "trap_id": "damage_trap", "level": 2, "required": False},
            "retry": {"max_count": 0},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        mock_press.assert_called_with("2", hold_ms=4000, overlay=None)
        assert ctx["state"]["trap_levels"]["damage_trap"] == 2

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.action.press_key")
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    def test_fallback_to_trap_config(self, mock_map, mock_press, mock_sleep) -> None:
        ctx = _make_context()
        action = {
            "type": "upgrade_trap",
            "trap_id": "slow_trap",
            "target_level": 2,
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "execute": {},
            "verify": {"type": "trap_level_gte", "trap_id": "slow_trap", "level": 2, "required": False},
            "retry": {"max_count": 0},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        mock_press.assert_called_with("1", hold_ms=4000, overlay=None)

    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    def test_condition_skip(self, mock_map) -> None:
        ctx = _make_context()
        action = {
            "type": "upgrade_trap",
            "trap_id": "damage_trap",
            "target_level": 2,
            "conditions": {"resource_gte": 99999},
            "on_condition_failed": {"policy": "skip"},
            "execute": {"method": "hold_key", "key": "2", "hold_ms": 4000},
            "verify": {},
            "retry": {},
            "on_fail": {"policy": "skip"},
        }
        with patch.object(self.executor._condition_engine, "eval_conditions", return_value=False):
            result = self.executor.execute(action, ctx)
        assert result["skipped"] is True


class TestExecuteRemoveTrap:
    def setup_method(self) -> None:
        self.detector = MagicMock()
        self.executor = ActionExecutor(detector=self.detector)

    @patch("td_executor.engine.action.time.sleep")
    @patch("td_executor.engine.slot.click_slot", return_value=True)
    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot")
    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_default_click(self, mock_pan, mock_locate, mock_map, mock_click, mock_sleep) -> None:
        mock_locate.return_value = {"slot_id": "A01", "region_id": "entrance_left", "center_x": 867, "center_y": 605, "precision": {}, "verify": {}, "slot_type": "ground", "default_trap": "slow_trap"}
        self.detector.is_slot_empty.return_value = True
        ctx = _make_context()
        ctx["state"]["trap_levels"]["slow_trap"] = 1
        action = {
            "type": "remove_trap",
            "slot_id": "A01",
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "execute": {"method": "custom_steps", "steps": []},
            "verify": {"type": "slot_empty", "slot_id": "A01", "required": True},
            "retry": {"max_count": 0},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        mock_click.assert_called_with("A01", ctx["rect"], ctx["slots"], overlay=None)

    @patch("td_executor.engine.action.ensure_map_open", return_value=True)
    @patch("td_executor.engine.slot.locate_slot")
    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_custom_steps_not_empty(self, mock_pan, mock_locate, mock_map) -> None:
        mock_locate.return_value = {"slot_id": "A01", "region_id": "entrance_left", "center_x": 867, "center_y": 605, "precision": {}, "verify": {}, "slot_type": "ground", "default_trap": "slow_trap"}
        ctx = _make_context()
        action = {
            "type": "remove_trap",
            "slot_id": "A01",
            "conditions": {},
            "on_condition_failed": {"policy": "skip"},
            "execute": {"method": "custom_steps", "steps": [{"type": "press_key", "key": "x"}]},
            "verify": {},
            "retry": {},
            "on_fail": {"policy": "skip"},
        }
        result = self.executor.execute(action, ctx)
        assert result["success"] is False
        assert result["skipped"] is True
        assert "custom_steps not implemented" in result["error"]


class TestExecutePanToRegion:
    def setup_method(self) -> None:
        self.executor = ActionExecutor()

    @patch("td_executor.engine.navigator.pan_to_region", return_value=True)
    def test_success(self, mock_pan) -> None:
        ctx = _make_context()
        action = {"type": "pan_to_region", "region_id": "entrance_left", "retry": {"max_count": 0}, "on_fail": {"policy": "skip"}}
        result = self.executor.execute(action, ctx)
        assert result["success"] is True
        mock_pan.assert_called_once()

    @patch("td_executor.engine.navigator.pan_to_region", return_value=False)
    def test_failure(self, mock_pan) -> None:
        ctx = _make_context()
        action = {"type": "pan_to_region", "region_id": "entrance_left", "retry": {"max_count": 0}, "on_fail": {"policy": "skip"}}
        result = self.executor.execute(action, ctx)
        assert result["success"] is False
        assert "pan_to_region failed" in result.get("error", "")


class TestBuildVerifyFn:
    def setup_method(self) -> None:
        self.detector = MagicMock()
        self.executor = ActionExecutor(detector=self.detector)

    def test_slot_has_trap(self) -> None:
        self.detector.is_slot_occupied.return_value = True
        action = {"verify": {"type": "slot_has_trap", "slot_id": "A01", "required": True}}
        ctx = _make_context()
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True
        self.detector.is_slot_occupied.assert_called_once()

    def test_slot_empty(self) -> None:
        self.detector.is_slot_empty.return_value = True
        action = {"verify": {"type": "slot_empty", "slot_id": "A01", "required": True}}
        ctx = _make_context()
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True
        self.detector.is_slot_empty.assert_called_once()

    def test_trap_level_gte_with_state(self) -> None:
        action = {"verify": {"type": "trap_level_gte", "trap_id": "damage_trap", "level": 2, "required": True}}
        ctx = _make_context(state={"trap_levels": {"damage_trap": 3}})
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True

    def test_trap_level_gte_required_false(self) -> None:
        action = {"verify": {"type": "trap_level_gte", "trap_id": "damage_trap", "level": 2, "required": False}}
        ctx = _make_context(state={"trap_levels": {}})
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True

    def test_trap_level_gte_required_true_no_data(self) -> None:
        action = {"verify": {"type": "trap_level_gte", "trap_id": "damage_trap", "level": 2, "required": True}}
        ctx = _make_context(state={"trap_levels": {}})
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is False

    def test_empty_verify(self) -> None:
        action = {"verify": {}}
        ctx = _make_context()
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True

    def test_unknown_verify_type_required_false(self) -> None:
        action = {"verify": {"type": "unknown", "required": False}}
        ctx = _make_context()
        fn = self.executor._build_verify_fn(action, ctx)
        assert fn(None) is True


class TestModuleLevelExecuteAction:
    def test_log_action(self) -> None:
        result = execute_action({"type": "log", "message": "test"}, {})
        assert result["success"] is True


class TestEngineExports:
    def test_import_action_executor(self) -> None:
        from td_executor.engine import ActionExecutor
        assert ActionExecutor is not None
