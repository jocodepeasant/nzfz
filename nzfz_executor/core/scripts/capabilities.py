"""Basic Profile 能力声明（P2-10）。"""

from __future__ import annotations

SUPPORTED_CAPABILITIES_BASIC = frozenset(
    {
        "script_load",
        "script_validate",
        "viewport_ratio_coordinate",
        "manual_wave_driver",
        "map_open_close",
        "reset_view_to_origin",
        "pan_to_region",
        "place_trap",
        "wait_action",
        "log_action",
        "retry_basic",
        "condition_basic",
        "dry_run",
    },
)
