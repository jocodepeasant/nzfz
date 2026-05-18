from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from td_executor.engine.condition import (
    ConditionContext,
    ConditionEngine,
    _find_slot,
    eval_conditions,
)


def _make_ctx(**overrides) -> ConditionContext:
    defaults = {
        "capture": MagicMock(),
        "rect": MagicMock(),
        "rois": {},
        "slots": [],
        "traps": [],
    }
    defaults.update(overrides)
    return ConditionContext(**defaults)


class TestConditionContext:
    def test_instantiation_with_required_fields(self) -> None:
        ctx = _make_ctx()
        assert ctx.capture is not None
        assert ctx.rect is not None
        assert ctx.rois == {}
        assert ctx.slots == []
        assert ctx.traps == []

    def test_optional_fields_default_to_none(self) -> None:
        ctx = _make_ctx()
        assert ctx.state is None
        assert ctx.multi_frame is None

    def test_optional_fields_can_be_set(self) -> None:
        ctx = _make_ctx(state={"trap_levels": {}}, multi_frame={"wave_frames": 3})
        assert ctx.state == {"trap_levels": {}}
        assert ctx.multi_frame == {"wave_frames": 3}


class TestEmptyConditions:
    def test_empty_dict_returns_true(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({}, ctx) is True

    def test_none_returns_true(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions(None, ctx) is True


class TestResourceGte:
    @patch("td_executor.engine.condition.read_resource", return_value=100)
    def test_satisfied_when_resource_gte_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"resource_gte": 80}, ctx) is True

    @patch("td_executor.engine.condition.read_resource", return_value=50)
    def test_not_satisfied_when_resource_lt_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"resource_gte": 80}, ctx) is False

    @patch("td_executor.engine.condition.read_resource", return_value=80)
    def test_satisfied_when_resource_equal_to_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"resource_gte": 80}, ctx) is True

    @patch("td_executor.engine.condition.read_resource", return_value=None)
    def test_returns_false_when_ocr_returns_none(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"resource_gte": 80}, ctx) is False


class TestWaveEq:
    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_satisfied_when_wave_eq_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_eq": 5}, ctx) is True

    @patch("td_executor.engine.condition.read_wave", return_value=3)
    def test_not_satisfied_when_wave_neq_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_eq": 5}, ctx) is False

    @patch("td_executor.engine.condition.read_wave", return_value=None)
    def test_returns_false_when_ocr_returns_none(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_eq": 5}, ctx) is False


class TestWaveGte:
    @patch("td_executor.engine.condition.read_wave", return_value=7)
    def test_satisfied_when_wave_gte_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_gte": 5}, ctx) is True

    @patch("td_executor.engine.condition.read_wave", return_value=3)
    def test_not_satisfied_when_wave_lt_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_gte": 5}, ctx) is False

    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_satisfied_when_wave_equal_to_value(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_gte": 5}, ctx) is True

    @patch("td_executor.engine.condition.read_wave", return_value=None)
    def test_returns_false_when_ocr_returns_none(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        assert engine.eval_conditions({"wave_gte": 5}, ctx) is False


class TestSlotEmpty:
    def test_detector_returns_true(self) -> None:
        detector = MagicMock()
        detector.is_slot_empty.return_value = True
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {"check_area": {}}}])
        assert engine.eval_conditions({"slot_empty": "slot1"}, ctx) is True
        detector.is_slot_empty.assert_called_once_with(ctx.capture, ctx.rect, {"check_area": {}})

    def test_detector_returns_false(self) -> None:
        detector = MagicMock()
        detector.is_slot_empty.return_value = False
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {"check_area": {}}}])
        assert engine.eval_conditions({"slot_empty": "slot1"}, ctx) is False

    def test_no_detector_returns_false_with_warning(self) -> None:
        engine = ConditionEngine(detector=None)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {}}])
        with patch("td_executor.engine.condition.logger") as mock_logger:
            result = engine.eval_conditions({"slot_empty": "slot1"}, ctx)
            assert result is False
            mock_logger.warning.assert_called()

    def test_slot_not_found_returns_false_with_warning(self) -> None:
        detector = MagicMock()
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "other_slot", "verify": {}}])
        with patch("td_executor.engine.condition.logger") as mock_logger:
            result = engine.eval_conditions({"slot_empty": "slot1"}, ctx)
            assert result is False
            mock_logger.warning.assert_called()

    def test_slot_without_verify_uses_empty_dict(self) -> None:
        detector = MagicMock()
        detector.is_slot_empty.return_value = True
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1"}])
        assert engine.eval_conditions({"slot_empty": "slot1"}, ctx) is True
        detector.is_slot_empty.assert_called_once_with(ctx.capture, ctx.rect, {})


class TestSlotOccupied:
    def test_detector_returns_true(self) -> None:
        detector = MagicMock()
        detector.is_slot_occupied.return_value = True
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {"check_area": {}}}])
        assert engine.eval_conditions({"slot_occupied": "slot1"}, ctx) is True
        detector.is_slot_occupied.assert_called_once_with(ctx.capture, ctx.rect, {"check_area": {}})

    def test_detector_returns_false(self) -> None:
        detector = MagicMock()
        detector.is_slot_occupied.return_value = False
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {"check_area": {}}}])
        assert engine.eval_conditions({"slot_occupied": "slot1"}, ctx) is False

    def test_no_detector_returns_false_with_warning(self) -> None:
        engine = ConditionEngine(detector=None)
        ctx = _make_ctx(slots=[{"slot_id": "slot1", "verify": {}}])
        with patch("td_executor.engine.condition.logger") as mock_logger:
            result = engine.eval_conditions({"slot_occupied": "slot1"}, ctx)
            assert result is False
            mock_logger.warning.assert_called()

    def test_slot_not_found_returns_false_with_warning(self) -> None:
        detector = MagicMock()
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "other_slot", "verify": {}}])
        with patch("td_executor.engine.condition.logger") as mock_logger:
            result = engine.eval_conditions({"slot_occupied": "slot1"}, ctx)
            assert result is False
            mock_logger.warning.assert_called()

    def test_slot_without_verify_uses_empty_dict(self) -> None:
        detector = MagicMock()
        detector.is_slot_occupied.return_value = True
        engine = ConditionEngine(detector=detector)
        ctx = _make_ctx(slots=[{"slot_id": "slot1"}])
        assert engine.eval_conditions({"slot_occupied": "slot1"}, ctx) is True
        detector.is_slot_occupied.assert_called_once_with(ctx.capture, ctx.rect, {})


class TestTrapLevelLt:
    @pytest.mark.parametrize(
        "current_level,threshold,expected",
        [
            (1, 3, True),
            (2, 2, False),
            (3, 2, False),
            (0, 1, True),
        ],
    )
    def test_level_comparison(self, current_level: int, threshold: int, expected: bool) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_a": current_level}})
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a", "level": threshold}}, ctx
        )
        assert result is expected

    def test_returns_true_when_state_is_none(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state=None)
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a", "level": 3}}, ctx
        )
        assert result is True

    def test_returns_true_when_trap_levels_missing_entry(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_b": 1}})
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a", "level": 3}}, ctx
        )
        assert result is True

    def test_returns_true_when_value_missing_trap_id(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_a": 1}})
        result = engine.eval_conditions(
            {"trap_level_lt": {"level": 3}}, ctx
        )
        assert result is True

    def test_returns_true_when_value_missing_level(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_a": 1}})
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a"}}, ctx
        )
        assert result is True

    def test_returns_true_when_value_empty_dict(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_a": 1}})
        result = engine.eval_conditions(
            {"trap_level_lt": {}}, ctx
        )
        assert result is True

    def test_returns_true_when_state_empty_dict(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={})
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a", "level": 3}}, ctx
        )
        assert result is True

    def test_returns_true_when_trap_levels_empty(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {}})
        result = engine.eval_conditions(
            {"trap_level_lt": {"trap_id": "trap_a", "level": 3}}, ctx
        )
        assert result is True


class TestUnknownConditionKey:
    def test_unknown_key_does_not_crash(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        result = engine.eval_conditions({"unknown_key": 42}, ctx)
        assert result is True

    def test_unknown_key_does_not_return_false(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        with patch("td_executor.engine.condition.logger") as mock_logger:
            result = engine.eval_conditions({"unknown_key": 42}, ctx)
            assert result is True
            mock_logger.warning.assert_called()

    def test_unknown_key_mixed_with_valid_conditions(self) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx(state={"trap_levels": {"trap_a": 1}})
        result = engine.eval_conditions(
            {"unknown_key": 42, "trap_level_lt": {"trap_id": "trap_a", "level": 3}}, ctx
        )
        assert result is True


class TestOcrCaching:
    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_wave_read_once_when_both_wave_eq_and_wave_gte(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        result = engine.eval_conditions({"wave_eq": 5, "wave_gte": 3}, ctx)
        assert result is True
        assert mock_read.call_count == 1

    @patch("td_executor.engine.condition.read_resource", return_value=100)
    def test_resource_read_once_when_repeated(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        result = engine.eval_conditions({"resource_gte": 50, "resource_gte": 80}, ctx)
        assert mock_read.call_count <= 1

    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_cache_reset_between_eval_calls(self, mock_read: MagicMock) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        engine.eval_conditions({"wave_eq": 5}, ctx)
        engine.eval_conditions({"wave_eq": 5}, ctx)
        assert mock_read.call_count == 2


class TestShortCircuitEvaluation:
    @patch("td_executor.engine.condition.read_wave", return_value=3)
    @patch("td_executor.engine.condition.read_resource", return_value=100)
    def test_first_condition_fails_skips_second(
        self, mock_resource: MagicMock, mock_wave: MagicMock
    ) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        result = engine.eval_conditions(
            {"wave_eq": 5, "resource_gte": 50}, ctx
        )
        assert result is False
        assert mock_wave.call_count == 1
        assert mock_resource.call_count == 0

    @patch("td_executor.engine.condition.read_resource", return_value=10)
    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_first_passes_second_fails(
        self, mock_wave: MagicMock, mock_resource: MagicMock
    ) -> None:
        engine = ConditionEngine()
        ctx = _make_ctx()
        result = engine.eval_conditions(
            {"wave_eq": 5, "resource_gte": 50}, ctx
        )
        assert result is False
        assert mock_wave.call_count == 1
        assert mock_resource.call_count == 1


class TestFindSlot:
    def test_finds_matching_slot(self) -> None:
        slots = [
            {"slot_id": "slot1", "verify": {"a": 1}},
            {"slot_id": "slot2", "verify": {"b": 2}},
        ]
        result = _find_slot(slots, "slot2")
        assert result == {"slot_id": "slot2", "verify": {"b": 2}}

    def test_returns_none_when_not_found(self) -> None:
        slots = [{"slot_id": "slot1", "verify": {}}]
        result = _find_slot(slots, "slot_missing")
        assert result is None

    def test_empty_slots_list(self) -> None:
        result = _find_slot([], "slot1")
        assert result is None

    def test_slot_without_slot_id_key(self) -> None:
        slots = [{"name": "slot1", "verify": {}}]
        result = _find_slot(slots, "slot1")
        assert result is None


class TestModuleLevelEvalConditions:
    @patch("td_executor.engine.condition.read_resource", return_value=200)
    def test_delegates_to_engine(self, mock_read: MagicMock) -> None:
        capture = MagicMock()
        rect = MagicMock()
        rois = {"resource": {}}
        result = eval_conditions(
            {"resource_gte": 100},
            capture,
            rect,
            rois,
            slots=[],
            traps=[],
        )
        assert result is True

    @patch("td_executor.engine.condition.read_wave", return_value=5)
    def test_with_state(self, mock_read: MagicMock) -> None:
        capture = MagicMock()
        rect = MagicMock()
        rois = {"wave": {}}
        result = eval_conditions(
            {"wave_eq": 5},
            capture,
            rect,
            rois,
            slots=[],
            traps=[],
            state={"trap_levels": {}},
        )
        assert result is True

    def test_empty_conditions(self) -> None:
        capture = MagicMock()
        rect = MagicMock()
        result = eval_conditions({}, capture, rect, {}, [], [])
        assert result is True
