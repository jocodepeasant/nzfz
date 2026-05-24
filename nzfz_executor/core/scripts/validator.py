"""塔防脚本校验（P2-10）。"""

from __future__ import annotations

from nzfz_executor.core.scripts.capabilities import SUPPORTED_CAPABILITIES_BASIC
from nzfz_executor.core.scripts.constants import (
    COORDINATE_MODE_COMPATIBLE,
    GAME_MODE_TOWER_DEFENSE,
    PROFILE_TOWER_DEFENSE_V1_BASIC,
    SCHEMA_VERSION,
    SUPPORTED_ENABLED_ACTION_TYPES_BASIC,
    UNSUPPORTED_ENABLED_ACTION_TYPES_BASIC,
)
from nzfz_executor.core.scripts.models import (
    ScriptDefinition,
    ScriptIndexes,
    ScriptValidationResult,
)


def _is_valid_ratio(value: object) -> bool:
    if not isinstance(value, (int, float)):
        return False
    return 0.0 <= float(value) <= 1.0


class ScriptValidator:
    """Basic Profile 脚本校验器。"""

    def validate(
        self,
        script: ScriptDefinition,
        indexes: ScriptIndexes,
        *,
        strict_compatibility: bool = False,
    ) -> ScriptValidationResult:
        warnings: list[str] = []
        errors: list[str] = []

        if script.schema_version != SCHEMA_VERSION:
            errors.append(
                f"schema_version 必须为 {SCHEMA_VERSION}，当前为 {script.schema_version}",
            )

        if script.game_mode != GAME_MODE_TOWER_DEFENSE:
            errors.append(
                f"game_mode 必须为 {GAME_MODE_TOWER_DEFENSE}，当前为 {script.game_mode}",
            )

        if script.compatibility.profile != PROFILE_TOWER_DEFENSE_V1_BASIC:
            errors.append(
                "compatibility.profile 必须为 "
                f"{PROFILE_TOWER_DEFENSE_V1_BASIC}，"
                f"当前为 {script.compatibility.profile}",
            )

        missing_caps = [
            cap
            for cap in script.compatibility.required_capabilities
            if cap not in SUPPORTED_CAPABILITIES_BASIC
        ]
        if missing_caps:
            errors.append(
                "required_capabilities 包含执行器不支持的能力："
                + ", ".join(missing_caps),
            )

        if script.map.coordinate_mode not in COORDINATE_MODE_COMPATIBLE:
            errors.append(
                "map.coordinate_mode 不支持："
                f"{script.map.coordinate_mode}",
            )

        if len(script.map.floors) > 1:
            errors.append(
                "Basic Profile 不支持多楼层："
                f"floors.length={len(script.map.floors)}",
            )

        if script.recognition.templates:
            warnings.append("templates 存在但 Basic Profile 不使用")

        if script.recognition.color_rules:
            warnings.append("color_rules 存在但 Basic Profile 不使用")

        if script.recognition.rois:
            warnings.append("rois 存在但 Basic Profile 不使用")

        for slot in script.slots:
            pos = slot.position
            if not _is_valid_ratio(pos.x_ratio) or not _is_valid_ratio(pos.y_ratio):
                errors.append(
                    f"slot.position ratio 越界：slot_id={slot.slot_id}",
                )
            if slot.region_id not in indexes.regions_by_id:
                errors.append(
                    f"slot.region_id 不存在：slot_id={slot.slot_id}, "
                    f"region_id={slot.region_id}",
                )
            elif slot.floor_id != indexes.regions_by_id[slot.region_id].floor_id:
                errors.append(
                    f"slot.floor_id 与 region.floor_id 不一致："
                    f"slot_id={slot.slot_id}",
                )

        for wave in script.waves:
            for action in wave.actions:
                self._validate_action(
                    action=action,
                    indexes=indexes,
                    warnings=warnings,
                    errors=errors,
                    strict_compatibility=strict_compatibility,
                )

        return ScriptValidationResult(
            success=len(errors) == 0,
            warnings=warnings,
            errors=errors,
        )

    def _validate_action(
        self,
        *,
        action,
        indexes: ScriptIndexes,
        warnings: list[str],
        errors: list[str],
        strict_compatibility: bool,
    ) -> None:
        if not action.enabled:
            warnings.append(
                f"disabled action 将跳过：action_id={action.action_id}, "
                f"type={action.type}",
            )
            return

        action_type = action.type
        if action_type in UNSUPPORTED_ENABLED_ACTION_TYPES_BASIC:
            errors.append(
                f"enabled=true 的 action 类型不支持："
                f"action_id={action.action_id}, type={action_type}",
            )
            return

        if action_type not in SUPPORTED_ENABLED_ACTION_TYPES_BASIC:
            errors.append(
                f"enabled=true 的 action 类型不支持："
                f"action_id={action.action_id}, type={action_type}",
            )
            return

        raw = action.raw
        conditions = raw.get("conditions")
        if conditions:
            message = (
                f"action.conditions 存在，Basic Profile 将视为通过："
                f"action_id={action.action_id}"
            )
            if strict_compatibility:
                errors.append(message)
            else:
                warnings.append(message)

        verify = raw.get("verify")
        if verify:
            warnings.append(
                f"action.verify 存在，Basic Profile 将跳过："
                f"action_id={action.action_id}",
            )

        retry = raw.get("retry") or {}
        max_attempts = retry.get("max_attempts")
        if max_attempts is not None and int(max_attempts) < 1:
            errors.append(
                f"retry.max_attempts 必须 >= 1：action_id={action.action_id}",
            )
        if retry.get("reset_view_before_retry"):
            warnings.append(
                f"retry.reset_view_before_retry=true 已忽略："
                f"action_id={action.action_id}",
            )
        if retry.get("micro_adjust_on_retry"):
            warnings.append(
                f"retry.micro_adjust_on_retry=true 已忽略："
                f"action_id={action.action_id}",
            )

        if action_type == "place_trap":
            trap_id = raw.get("trap_id")
            slot_id = raw.get("slot_id")
            if not trap_id or trap_id not in indexes.traps_by_id:
                errors.append(
                    f"place_trap.trap_id 不存在：action_id={action.action_id}, "
                    f"trap_id={trap_id}",
                )
            if not slot_id or slot_id not in indexes.slots_by_id:
                errors.append(
                    f"place_trap.slot_id 不存在：action_id={action.action_id}, "
                    f"slot_id={slot_id}",
                )

        if action_type == "pan_to_region":
            region_id = raw.get("region_id")
            if not region_id or region_id not in indexes.regions_by_id:
                errors.append(
                    f"pan_to_region.region_id 不存在："
                    f"action_id={action.action_id}, region_id={region_id}",
                )
