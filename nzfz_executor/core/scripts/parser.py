"""塔防脚本 JSON 解析（P2-10）。"""

from __future__ import annotations

from typing import Any

from nzfz_executor.core.scripts.models import (
    CompatibilityDefinition,
    FloorDefinition,
    InitialViewDefinition,
    MapDefinition,
    PackageDefinition,
    RatioPoint,
    RecognitionDefinition,
    RegionDefinition,
    RuntimeDefinition,
    ScriptAction,
    ScriptDefinition,
    SlotDefinition,
    TemplateDefinition,
    TrapDefinition,
    WaveDefinition,
)


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} 必须是对象")
    return value


def _parse_ratio_point(raw: Any, field_name: str) -> RatioPoint:
    data = _require_dict(raw, field_name)
    return RatioPoint(
        x_ratio=float(data.get("x_ratio", 0)),
        y_ratio=float(data.get("y_ratio", 0)),
    )


def parse_script_definition(raw: dict[str, Any]) -> ScriptDefinition:
    """将 JSON 根对象解析为 ScriptDefinition。"""
    compatibility_raw = _require_dict(raw.get("compatibility"), "compatibility")
    package_raw = _require_dict(raw.get("package"), "package")
    map_raw = _require_dict(raw.get("map"), "map")
    runtime_raw = _require_dict(raw.get("runtime"), "runtime")
    recognition_raw = _require_dict(raw.get("recognition"), "recognition")

    base_resolution = _require_dict(
        map_raw.get("base_resolution"),
        "map.base_resolution",
    )
    initial_view_raw = _require_dict(
        map_raw.get("initial_view"),
        "map.initial_view",
    )

    floors = [
        FloorDefinition(
            floor_id=str(item.get("floor_id", "")),
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
        )
        for item in map_raw.get("floors") or []
        if isinstance(item, dict)
    ]

    templates = [
        TemplateDefinition(
            template_id=str(item.get("template_id", "")),
            name=str(item.get("name", item.get("template_id", ""))),
            path=str(item.get("path", "")),
            threshold=float(item.get("threshold", 0.85)),
            roi=item.get("roi"),
            grayscale=bool(item.get("grayscale", True)),
            raw=item,
        )
        for item in recognition_raw.get("templates") or []
        if isinstance(item, dict)
    ]

    traps = [
        TrapDefinition(
            trap_id=str(item.get("trap_id", "")),
            trap_name=str(item.get("trap_name", item.get("trap_id", ""))),
            select_key=str(item.get("select_key", "")),
            upgrade_key=str(item.get("upgrade_key", "")),
            upgrade_hold_ms=int(item.get("upgrade_hold_ms", 4000)),
            cost=int(item.get("cost", 0)),
            upgrade_cost=int(item.get("upgrade_cost", 0)),
            max_level=int(item.get("max_level", 1)),
            upgrade_mode=str(item.get("upgrade_mode", "all_same_type")),
            recognition=dict(item.get("recognition") or {}),
            raw=item,
        )
        for item in raw.get("traps") or []
        if isinstance(item, dict)
    ]

    regions = [
        RegionDefinition(
            region_id=str(item.get("region_id", "")),
            floor_id=str(item.get("floor_id", "")),
            name=str(item.get("name", item.get("region_id", ""))),
            description=str(item.get("description", "")),
            enter_policy=dict(item.get("enter_policy") or {}),
            enter_actions=[
                action
                for action in item.get("enter_actions") or []
                if isinstance(action, dict)
            ],
            raw=item,
        )
        for item in raw.get("regions") or []
        if isinstance(item, dict)
    ]

    slots = [
        SlotDefinition(
            slot_id=str(item.get("slot_id", "")),
            floor_id=str(item.get("floor_id", "")),
            name=str(item.get("name", item.get("slot_id", ""))),
            region_id=str(item.get("region_id", "")),
            position=_parse_ratio_point(
                item.get("position"),
                f"slots[{item.get('slot_id')}].position",
            ),
            precision=dict(item.get("precision") or {}),
            slot_type=str(item.get("slot_type", "ground")),
            default_trap=str(item.get("default_trap", "")),
            verify=dict(item.get("verify") or {}),
            raw=item,
        )
        for item in raw.get("slots") or []
        if isinstance(item, dict)
    ]

    waves: list[WaveDefinition] = []
    for item in raw.get("waves") or []:
        if not isinstance(item, dict):
            continue
        actions = [
            ScriptAction(
                action_id=str(action.get("action_id", "")),
                type=str(action.get("type", "")),
                enabled=bool(action.get("enabled", True)),
                name=str(action.get("name", action.get("action_id", ""))),
                raw=action,
            )
            for action in item.get("actions") or []
            if isinstance(action, dict)
        ]
        waves.append(
            WaveDefinition(
                wave=int(item.get("wave", 0)),
                name=str(item.get("name", "")),
                execute_once=bool(item.get("execute_once", True)),
                trigger=dict(item.get("trigger") or {}),
                actions=actions,
                raw=item,
            ),
        )

    return ScriptDefinition(
        schema_version=str(raw.get("schema_version", "")),
        script_id=str(raw.get("script_id", "")),
        script_name=str(raw.get("script_name", "")),
        game_mode=str(raw.get("game_mode", "")),
        compatibility=CompatibilityDefinition(
            executor_min_version=str(
                compatibility_raw.get("executor_min_version", ""),
            ),
            profile=str(compatibility_raw.get("profile", "")),
            required_capabilities=[
                str(cap)
                for cap in compatibility_raw.get("required_capabilities") or []
            ],
            optional_capabilities=[
                str(cap)
                for cap in compatibility_raw.get("optional_capabilities") or []
            ],
        ),
        package=PackageDefinition(
            type=str(package_raw.get("type", "directory")),
            resource_base=str(package_raw.get("resource_base", ".")),
            template_dir=str(package_raw.get("template_dir", "templates")),
            preview_dir=str(package_raw.get("preview_dir", "previews")),
            path_rule=str(
                package_raw.get("path_rule", "relative_to_script_json"),
            ),
        ),
        map=MapDefinition(
            map_id=str(map_raw.get("map_id", "")),
            map_name=str(map_raw.get("map_name", "")),
            difficulty=str(map_raw.get("difficulty", "normal")),
            strategy_id=str(map_raw.get("strategy_id", "baseline")),
            base_resolution_width=int(base_resolution.get("width", 1920)),
            base_resolution_height=int(base_resolution.get("height", 1080)),
            coordinate_mode=str(
                map_raw.get("coordinate_mode", "viewport_ratio_after_region_enter"),
            ),
            floors=floors,
            default_floor_id=str(map_raw.get("default_floor_id", "")),
            initial_view=InitialViewDefinition(
                type=str(initial_view_raw.get("type", "")),
                origin_region_id=str(
                    initial_view_raw.get("origin_region_id", "origin"),
                ),
            ),
        ),
        runtime=RuntimeDefinition(
            max_run_minutes=int(runtime_raw.get("max_run_minutes", 30)),
            default_action_timeout_ms=int(
                runtime_raw.get("default_action_timeout_ms", 8000),
            ),
            default_retry_count=int(runtime_raw.get("default_retry_count", 2)),
            default_resource_policy=str(
                runtime_raw.get("default_resource_policy", "wait"),
            ),
            default_wait_resource_timeout_ms=int(
                runtime_raw.get("default_wait_resource_timeout_ms", 30000),
            ),
            condition_check_interval_ms=int(
                runtime_raw.get("condition_check_interval_ms", 500),
            ),
            poll_interval_ms=int(runtime_raw.get("poll_interval_ms", 500)),
            wave_stable_frames=int(runtime_raw.get("wave_stable_frames", 3)),
            wait_after_pan_ms=int(runtime_raw.get("wait_after_pan_ms", 800)),
            wait_after_place_ms=int(runtime_raw.get("wait_after_place_ms", 600)),
            wait_after_remove_ms=int(runtime_raw.get("wait_after_remove_ms", 600)),
            wait_after_upgrade_ms=int(runtime_raw.get("wait_after_upgrade_ms", 1000)),
            reset_view_on_retry=bool(runtime_raw.get("reset_view_on_retry", True)),
        ),
        recognition=RecognitionDefinition(
            rois=dict(recognition_raw.get("rois") or {}),
            templates=templates,
            color_rules=[
                item
                for item in recognition_raw.get("color_rules") or []
                if isinstance(item, dict)
            ],
            multi_frame=dict(recognition_raw.get("multi_frame") or {}),
        ),
        traps=traps,
        regions=regions,
        slots=slots,
        waves=waves,
        raw=raw,
    )
