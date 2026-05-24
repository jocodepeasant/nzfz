"""塔防脚本协议常量（P2-10）。"""

from __future__ import annotations

SCHEMA_VERSION = "1.1.0"
GAME_MODE_TOWER_DEFENSE = "tower_defense"
PROFILE_TOWER_DEFENSE_V1_BASIC = "tower_defense_v1_basic"

COORDINATE_MODE_VIEWPORT_RATIO = "viewport_ratio_after_region_enter"
COORDINATE_MODE_COMPATIBLE = frozenset(
    {
        COORDINATE_MODE_VIEWPORT_RATIO,
        "region_screen_ratio",
    },
)

SUPPORTED_ENABLED_ACTION_TYPES_BASIC = frozenset(
    {
        "place_trap",
        "wait",
        "log",
        "pan_to_region",
    },
)

UNSUPPORTED_ENABLED_ACTION_TYPES_BASIC = frozenset(
    {
        "upgrade_trap",
        "remove_trap",
    },
)

REGION_ENTER_ACTION_TYPES = frozenset(
    {
        "reset_view_to_origin",
        "drag_ratio",
        "wait",
    },
)

SCRIPT_EXECUTION_MODE_SEQUENTIAL = "sequential"
SCRIPT_EXECUTION_MODE_SINGLE_WAVE = "single_wave"

SUPPORTED_SCRIPT_EXECUTION_MODES = frozenset(
    {
        SCRIPT_EXECUTION_MODE_SEQUENTIAL,
        SCRIPT_EXECUTION_MODE_SINGLE_WAVE,
    },
)

DEFAULT_RETRY_INTERVAL_MS = 800
DEFAULT_WAIT_AFTER_SELECT_TRAP_MS = 150
DEFAULT_MAP_RESET_SEQUENCE: list[dict[str, object]] = [
    {"type": "press_key", "key": "o", "wait_ms": 500},
]
