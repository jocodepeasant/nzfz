"""动作前置条件判断：支持资源、波次、格子状态、陷阱等级等条件。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from td_executor.runtime.capture import ScreenCapture
    from td_executor.runtime.window import WindowRect
    from td_executor.vision.detector import VisionDetector

from td_executor.vision.ocr import read_resource, read_wave

logger = logging.getLogger(__name__)

_SENTINEL = object()


@dataclass
class ConditionContext:
    capture: ScreenCapture
    rect: WindowRect
    rois: dict
    slots: list[dict]
    traps: list[dict]
    state: dict | None = None
    multi_frame: dict | None = None


class ConditionEngine:
    """条件引擎：根据条件字典短路求值。"""

    def __init__(self, detector: VisionDetector | None = None) -> None:
        self._detector = detector
        self._wave_cache: int | None | object = _SENTINEL
        self._resource_cache: int | None | object = _SENTINEL

    def eval_conditions(
        self, conditions: dict[str, Any] | None, ctx: ConditionContext
    ) -> bool:
        if not conditions:
            return True

        self._wave_cache = _SENTINEL
        self._resource_cache = _SENTINEL

        for key, value in conditions.items():
            result = self._eval_one(key, value, ctx)
            if result is None:
                logger.warning("未知条件类型: %s，跳过", key)
                continue
            if not result:
                return False
        return True

    def _eval_one(self, key: str, value: Any, ctx: ConditionContext) -> bool | None:
        handler = {
            "resource_gte": self._check_resource_gte,
            "wave_eq": self._check_wave_eq,
            "wave_gte": self._check_wave_gte,
            "slot_empty": self._check_slot_empty,
            "slot_occupied": self._check_slot_occupied,
            "trap_level_lt": self._check_trap_level_lt,
        }.get(key)
        if handler is None:
            return None
        return handler(value, ctx)

    def _get_resource(self, ctx: ConditionContext) -> int | None:
        if self._resource_cache is not _SENTINEL:
            return self._resource_cache
        self._resource_cache = read_resource(
            ctx.capture, ctx.rect, ctx.rois, ctx.multi_frame
        )
        return self._resource_cache

    def _get_wave(self, ctx: ConditionContext) -> int | None:
        if self._wave_cache is not _SENTINEL:
            return self._wave_cache
        self._wave_cache = read_wave(
            ctx.capture, ctx.rect, ctx.rois, ctx.multi_frame
        )
        return self._wave_cache

    def _check_resource_gte(self, value: int, ctx: ConditionContext) -> bool:
        resource = self._get_resource(ctx)
        if resource is None:
            return False
        return resource >= value

    def _check_wave_eq(self, value: int, ctx: ConditionContext) -> bool:
        wave = self._get_wave(ctx)
        if wave is None:
            return False
        return wave == value

    def _check_wave_gte(self, value: int, ctx: ConditionContext) -> bool:
        wave = self._get_wave(ctx)
        if wave is None:
            return False
        return wave >= value

    def _check_slot_empty(self, value: str, ctx: ConditionContext) -> bool:
        if self._detector is None:
            logger.warning("VisionDetector 未提供，slot_empty 条件返回 False")
            return False
        slot = _find_slot(ctx.slots, value)
        if slot is None:
            logger.warning("未找到 slot_id=%s，slot_empty 条件返回 False", value)
            return False
        verify = slot.get("verify", {})
        return self._detector.is_slot_empty(ctx.capture, ctx.rect, verify)

    def _check_slot_occupied(self, value: str, ctx: ConditionContext) -> bool:
        if self._detector is None:
            logger.warning("VisionDetector 未提供，slot_occupied 条件返回 False")
            return False
        slot = _find_slot(ctx.slots, value)
        if slot is None:
            logger.warning("未找到 slot_id=%s，slot_occupied 条件返回 False", value)
            return False
        verify = slot.get("verify", {})
        return self._detector.is_slot_occupied(ctx.capture, ctx.rect, verify)

    def _check_trap_level_lt(self, value: dict, ctx: ConditionContext) -> bool:
        trap_id = value.get("trap_id")
        level = value.get("level")
        if trap_id is None or level is None:
            logger.warning("trap_level_lt 条件缺少 trap_id 或 level")
            return True
        if not ctx.state:
            return True
        current_level = ctx.state.get("trap_levels", {}).get(trap_id)
        if current_level is None:
            return True
        return current_level < level


def _find_slot(slots: list[dict], slot_id: str) -> dict | None:
    for slot in slots:
        if slot.get("slot_id") == slot_id:
            return slot
    return None


def eval_conditions(
    conditions: dict[str, Any],
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    slots: list[dict],
    traps: list[dict],
    state: dict[str, Any] | None = None,
) -> bool:
    """模块级便捷函数：创建 ConditionEngine 并委托求值。"""
    ctx = ConditionContext(
        capture=capture,
        rect=rect,
        rois=rois,
        slots=slots,
        traps=traps,
        state=state,
    )
    engine = ConditionEngine()
    return engine.eval_conditions(conditions, ctx)
