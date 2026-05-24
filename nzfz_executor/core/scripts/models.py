"""塔防脚本数据模型（P2-10）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RatioPoint:
    x_ratio: float
    y_ratio: float


@dataclass(frozen=True)
class RatioRect:
    x_ratio: float
    y_ratio: float
    w_ratio: float
    h_ratio: float


@dataclass(frozen=True)
class CompatibilityDefinition:
    executor_min_version: str
    profile: str
    required_capabilities: list[str]
    optional_capabilities: list[str]


@dataclass(frozen=True)
class PackageDefinition:
    type: str
    resource_base: str
    template_dir: str
    preview_dir: str
    path_rule: str


@dataclass(frozen=True)
class FloorDefinition:
    floor_id: str
    name: str = ""
    description: str = ""


@dataclass(frozen=True)
class InitialViewDefinition:
    type: str
    origin_region_id: str


@dataclass(frozen=True)
class MapDefinition:
    map_id: str
    map_name: str
    difficulty: str
    strategy_id: str
    base_resolution_width: int
    base_resolution_height: int
    coordinate_mode: str
    floors: list[FloorDefinition]
    default_floor_id: str
    initial_view: InitialViewDefinition


@dataclass(frozen=True)
class RuntimeDefinition:
    max_run_minutes: int
    default_action_timeout_ms: int
    default_retry_count: int
    default_resource_policy: str
    default_wait_resource_timeout_ms: int
    condition_check_interval_ms: int
    poll_interval_ms: int
    wave_stable_frames: int
    wait_after_pan_ms: int
    wait_after_place_ms: int
    wait_after_remove_ms: int
    wait_after_upgrade_ms: int
    reset_view_on_retry: bool


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: str
    name: str
    path: str
    threshold: float
    roi: str | None
    grayscale: bool
    raw: dict[str, Any]


@dataclass(frozen=True)
class RecognitionDefinition:
    rois: dict[str, Any]
    templates: list[TemplateDefinition]
    color_rules: list[dict[str, Any]]
    multi_frame: dict[str, Any]


@dataclass(frozen=True)
class TrapDefinition:
    trap_id: str
    trap_name: str
    select_key: str
    upgrade_key: str
    upgrade_hold_ms: int
    cost: int
    upgrade_cost: int
    max_level: int
    upgrade_mode: str
    recognition: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class RegionDefinition:
    region_id: str
    floor_id: str
    name: str
    description: str
    enter_policy: dict[str, Any]
    enter_actions: list[dict[str, Any]]
    raw: dict[str, Any]


@dataclass(frozen=True)
class SlotDefinition:
    slot_id: str
    floor_id: str
    name: str
    region_id: str
    position: RatioPoint
    precision: dict[str, Any]
    slot_type: str
    default_trap: str
    verify: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ScriptAction:
    action_id: str
    type: str
    enabled: bool
    name: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class WaveDefinition:
    wave: int
    name: str
    execute_once: bool
    trigger: dict[str, Any]
    actions: list[ScriptAction]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ScriptDefinition:
    schema_version: str
    script_id: str
    script_name: str
    game_mode: str
    compatibility: CompatibilityDefinition
    package: PackageDefinition
    map: MapDefinition
    runtime: RuntimeDefinition
    recognition: RecognitionDefinition
    traps: list[TrapDefinition]
    regions: list[RegionDefinition]
    slots: list[SlotDefinition]
    waves: list[WaveDefinition]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ScriptIndexes:
    floors_by_id: dict[str, FloorDefinition]
    traps_by_id: dict[str, TrapDefinition]
    regions_by_id: dict[str, RegionDefinition]
    slots_by_id: dict[str, SlotDefinition]
    templates_by_id: dict[str, TemplateDefinition]
    actions_by_id: dict[str, ScriptAction]


@dataclass(frozen=True)
class ScriptValidationResult:
    success: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScriptLoadResult:
    success: bool
    script: ScriptDefinition | None = None
    indexes: ScriptIndexes | None = None
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
