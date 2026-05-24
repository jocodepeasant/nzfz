"""脚本索引构建（P2-10）。"""

from __future__ import annotations

from nzfz_executor.core.scripts.models import (
    FloorDefinition,
    RegionDefinition,
    ScriptAction,
    ScriptDefinition,
    ScriptIndexes,
    SlotDefinition,
    TemplateDefinition,
    TrapDefinition,
)


def build_script_indexes(script: ScriptDefinition) -> tuple[ScriptIndexes | None, list[str]]:
    """构建脚本索引；返回 (indexes, errors)。"""
    errors: list[str] = []

    floors_by_id: dict[str, FloorDefinition] = {}
    for floor in script.map.floors:
        if floor.floor_id in floors_by_id:
            errors.append(f"floor_id 重复：{floor.floor_id}")
        floors_by_id[floor.floor_id] = floor

    traps_by_id: dict[str, TrapDefinition] = {}
    for trap in script.traps:
        if trap.trap_id in traps_by_id:
            errors.append(f"trap_id 重复：{trap.trap_id}")
        traps_by_id[trap.trap_id] = trap

    regions_by_id: dict[str, RegionDefinition] = {}
    for region in script.regions:
        if region.region_id in regions_by_id:
            errors.append(f"region_id 重复：{region.region_id}")
        regions_by_id[region.region_id] = region

    slots_by_id: dict[str, SlotDefinition] = {}
    for slot in script.slots:
        if slot.slot_id in slots_by_id:
            errors.append(f"slot_id 重复：{slot.slot_id}")
        slots_by_id[slot.slot_id] = slot

    templates_by_id: dict[str, TemplateDefinition] = {}
    for template in script.recognition.templates:
        if template.template_id in templates_by_id:
            errors.append(f"template_id 重复：{template.template_id}")
        templates_by_id[template.template_id] = template

    actions_by_id: dict[str, ScriptAction] = {}
    for wave in script.waves:
        for action in wave.actions:
            if action.action_id in actions_by_id:
                errors.append(f"action_id 重复：{action.action_id}")
            actions_by_id[action.action_id] = action

    if errors:
        return None, errors

    return ScriptIndexes(
        floors_by_id=floors_by_id,
        traps_by_id=traps_by_id,
        regions_by_id=regions_by_id,
        slots_by_id=slots_by_id,
        templates_by_id=templates_by_id,
        actions_by_id=actions_by_id,
    ), []
