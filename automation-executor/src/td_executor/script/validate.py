"""Validate script dict against the shared JSON Schema."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator

_SCHEMA_JSON = r"""{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://nzfz.local/schemas/tower_defense_script_v1.schema.json",
  "title": "Tower Defense Automation Script V1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "script_id",
    "script_name",
    "game_mode",
    "map",
    "runtime",
    "recognition",
    "traps",
    "regions",
    "slots",
    "waves"
  ],
  "properties": {
    "schema_version": { "type": "string", "pattern": "^1\\.0\\.\\d+$" },
    "script_id": { "type": "string", "minLength": 1 },
    "script_name": { "type": "string", "minLength": 1 },
    "game_mode": { "type": "string", "const": "tower_defense" },
    "map": { "$ref": "#/$defs/map" },
    "runtime": { "$ref": "#/$defs/runtime" },
    "recognition": { "$ref": "#/$defs/recognition" },
    "traps": {
      "type": "array",
      "items": { "$ref": "#/$defs/trap" }
    },
    "regions": {
      "type": "array",
      "items": { "$ref": "#/$defs/region" }
    },
    "slots": {
      "type": "array",
      "items": { "$ref": "#/$defs/slot" }
    },
    "waves": {
      "type": "array",
      "items": { "$ref": "#/$defs/wave" }
    },
    "boss_reserved": { "type": "object" },
    "metadata": { "type": "object" }
  },
  "$defs": {
    "ratioRect": {
      "type": "object",
      "additionalProperties": false,
      "required": ["x_ratio", "y_ratio", "w_ratio", "h_ratio"],
      "properties": {
        "x_ratio": { "type": "number" },
        "y_ratio": { "type": "number" },
        "w_ratio": { "type": "number" },
        "h_ratio": { "type": "number" }
      }
    },
    "ratioPoint": {
      "type": "object",
      "additionalProperties": false,
      "required": ["x_ratio", "y_ratio"],
      "properties": {
        "x_ratio": { "type": "number" },
        "y_ratio": { "type": "number" }
      }
    },
    "mapFloor": {
      "type": "object",
      "additionalProperties": true,
      "required": ["floor_id", "name"],
      "properties": {
        "floor_id": { "type": "string", "minLength": 1 },
        "name": { "type": "string" },
        "base_resolution": {
          "type": "object",
          "additionalProperties": false,
          "required": ["width", "height"],
          "properties": {
            "width": { "type": "integer", "minimum": 1 },
            "height": { "type": "integer", "minimum": 1 }
          }
        },
        "editor_reference_image": {
          "type": "string",
          "description": "Configurator-only path or URI to floor screenshot; executor may ignore."
        }
      }
    },
    "map": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "map_id",
        "map_name",
        "difficulty",
        "strategy_id",
        "base_resolution",
        "coordinate_mode",
        "initial_view"
      ],
      "properties": {
        "map_id": { "type": "string" },
        "map_name": { "type": "string" },
        "difficulty": { "type": "string" },
        "strategy_id": { "type": "string" },
        "base_resolution": {
          "type": "object",
          "additionalProperties": false,
          "required": ["width", "height"],
          "properties": {
            "width": { "type": "integer", "minimum": 1 },
            "height": { "type": "integer", "minimum": 1 }
          }
        },
        "coordinate_mode": { "type": "string", "const": "region_screen_ratio" },
        "initial_view": {
          "type": "object",
          "additionalProperties": true,
          "required": ["type", "origin_region_id"],
          "properties": {
            "type": { "type": "string" },
            "origin_region_id": { "type": "string" }
          }
        },
        "default_floor_id": {
          "type": "string",
          "description": "When map.floors is present, slots/regions omitting floor_id use this floor."
        },
        "floors": {
          "type": "array",
          "description": "Optional multi-floor metadata; one reference image per floor in editor.",
          "items": { "$ref": "#/$defs/mapFloor" }
        },
        "calibration": {
          "type": "object",
          "additionalProperties": true,
          "description": "Optional window/content mapping. Recommended: content_rect (ratioRect on reference image), reference_image.",
          "properties": {
            "content_rect": { "$ref": "#/$defs/ratioRect" },
            "reference_image": { "type": "string" }
          }
        }
      }
    },
    "runtime": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "max_run_minutes",
        "default_action_timeout_ms",
        "default_retry_count",
        "default_resource_policy",
        "default_wait_resource_timeout_ms",
        "wait_after_pan_ms",
        "wait_after_place_ms",
        "wait_after_remove_ms",
        "wait_after_upgrade_ms",
        "reset_view_on_retry"
      ],
      "properties": {
        "max_run_minutes": { "type": "integer", "minimum": 1 },
        "default_action_timeout_ms": { "type": "integer", "minimum": 0 },
        "default_retry_count": { "type": "integer", "minimum": 0 },
        "default_resource_policy": { "type": "string" },
        "default_wait_resource_timeout_ms": { "type": "integer", "minimum": 0 },
        "wait_after_pan_ms": { "type": "integer", "minimum": 0 },
        "wait_after_place_ms": { "type": "integer", "minimum": 0 },
        "wait_after_remove_ms": { "type": "integer", "minimum": 0 },
        "wait_after_upgrade_ms": { "type": "integer", "minimum": 0 },
        "reset_view_on_retry": { "type": "boolean" }
      }
    },
    "recognition": {
      "type": "object",
      "additionalProperties": true,
      "required": ["rois", "multi_frame"],
      "properties": {
        "rois": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/ratioRect" }
        },
        "multi_frame": {
          "type": "object",
          "additionalProperties": { "type": "integer", "minimum": 1 }
        }
      }
    },
    "trap": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "trap_id",
        "trap_name",
        "select_key",
        "upgrade_key",
        "upgrade_hold_ms",
        "cost",
        "upgrade_cost",
        "max_level",
        "upgrade_mode"
      ],
      "properties": {
        "trap_id": { "type": "string" },
        "trap_name": { "type": "string" },
        "select_key": { "type": "string" },
        "upgrade_key": { "type": "string" },
        "upgrade_hold_ms": { "type": "integer", "minimum": 0 },
        "cost": { "type": "integer", "minimum": 0 },
        "upgrade_cost": { "type": "integer", "minimum": 0 },
        "max_level": { "type": "integer", "minimum": 1 },
        "upgrade_mode": { "type": "string" }
      }
    },
    "panMapAction": {
      "type": "object",
      "additionalProperties": true,
      "required": ["type", "direction", "distance_ratio", "duration_ms", "repeat"],
      "properties": {
        "type": { "const": "pan_map" },
        "direction": { "type": "string" },
        "distance_ratio": { "type": "number" },
        "duration_ms": { "type": "integer", "minimum": 0 },
        "repeat": { "type": "integer", "minimum": 1 }
      }
    },
    "region": {
      "type": "object",
      "additionalProperties": true,
      "required": ["region_id", "name", "description", "enter_actions"],
      "properties": {
        "floor_id": {
          "type": "string",
          "description": "Optional; ties region to map.floors[].floor_id when multi-floor."
        },
        "region_id": { "type": "string" },
        "name": { "type": "string" },
        "description": { "type": "string" },
        "enter_actions": {
          "type": "array",
          "items": {
            "oneOf": [{ "$ref": "#/$defs/panMapAction" }]
          }
        }
      }
    },
    "slot": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "slot_id",
        "name",
        "region_id",
        "position",
        "precision",
        "slot_type",
        "default_trap",
        "verify"
      ],
      "properties": {
        "floor_id": {
          "type": "string",
          "description": "Optional; ties slot to map.floors[].floor_id when multi-floor."
        },
        "slot_id": { "type": "string" },
        "name": { "type": "string" },
        "region_id": { "type": "string" },
        "position": { "$ref": "#/$defs/ratioPoint" },
        "precision": { "type": "object" },
        "slot_type": { "type": "string" },
        "default_trap": { "type": "string" },
        "verify": { "type": "object" }
      }
    },
    "retryBlock": {
      "type": "object",
      "additionalProperties": true,
      "properties": {
        "max_count": { "type": "integer", "minimum": 0 },
        "interval_ms": { "type": "integer", "minimum": 0 },
        "reset_view_before_retry": { "type": "boolean" },
        "micro_adjust_on_retry": { "type": "boolean" }
      }
    },
    "onConditionFailed": {
      "type": "object",
      "additionalProperties": true,
      "properties": {
        "policy": { "type": "string" },
        "timeout_ms": { "type": "integer" },
        "then": { "type": "string" }
      }
    },
    "onFail": {
      "type": "object",
      "additionalProperties": true,
      "required": ["policy"],
      "properties": {
        "policy": { "type": "string" }
      }
    },
    "waveTrigger": {
      "type": "object",
      "additionalProperties": true,
      "required": ["type"],
      "properties": {
        "type": { "type": "string" },
        "value": {}
      }
    },
    "actionPanToRegion": {
      "type": "object",
      "additionalProperties": true,
      "required": ["type", "region_id"],
      "properties": {
        "type": { "const": "pan_to_region" },
        "region_id": { "type": "string" },
        "retry": { "$ref": "#/$defs/retryBlock" }
      }
    },
    "actionPlaceTrap": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "type",
        "trap_id",
        "slot_id",
        "conditions",
        "on_condition_failed",
        "verify",
        "retry",
        "on_fail"
      ],
      "properties": {
        "type": { "const": "place_trap" },
        "name": { "type": "string" },
        "trap_id": { "type": "string" },
        "slot_id": { "type": "string" },
        "conditions": { "type": "object" },
        "on_condition_failed": { "$ref": "#/$defs/onConditionFailed" },
        "verify": { "type": "object" },
        "retry": { "$ref": "#/$defs/retryBlock" },
        "on_fail": { "$ref": "#/$defs/onFail" }
      }
    },
    "actionUpgradeTrap": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "type",
        "trap_id",
        "target_level",
        "conditions",
        "on_condition_failed",
        "execute",
        "verify",
        "retry",
        "on_fail"
      ],
      "properties": {
        "type": { "const": "upgrade_trap" },
        "name": { "type": "string" },
        "trap_id": { "type": "string" },
        "target_level": { "type": "integer", "minimum": 1 },
        "conditions": { "type": "object" },
        "on_condition_failed": { "$ref": "#/$defs/onConditionFailed" },
        "execute": { "type": "object" },
        "verify": { "type": "object" },
        "retry": { "$ref": "#/$defs/retryBlock" },
        "on_fail": { "$ref": "#/$defs/onFail" }
      }
    },
    "actionRemoveTrap": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "type",
        "slot_id",
        "conditions",
        "on_condition_failed",
        "execute",
        "verify",
        "retry",
        "on_fail"
      ],
      "properties": {
        "type": { "const": "remove_trap" },
        "name": { "type": "string" },
        "slot_id": { "type": "string" },
        "conditions": { "type": "object" },
        "on_condition_failed": { "$ref": "#/$defs/onConditionFailed" },
        "execute": { "type": "object" },
        "verify": { "type": "object" },
        "retry": { "$ref": "#/$defs/retryBlock" },
        "on_fail": { "$ref": "#/$defs/onFail" }
      }
    },
    "actionLog": {
      "type": "object",
      "additionalProperties": true,
      "required": ["type", "message"],
      "properties": {
        "type": { "const": "log" },
        "message": { "type": "string" }
      }
    },
    "waveAction": {
      "oneOf": [
        { "$ref": "#/$defs/actionPanToRegion" },
        { "$ref": "#/$defs/actionPlaceTrap" },
        { "$ref": "#/$defs/actionUpgradeTrap" },
        { "$ref": "#/$defs/actionRemoveTrap" },
        { "$ref": "#/$defs/actionLog" }
      ]
    },
    "wave": {
      "type": "object",
      "additionalProperties": true,
      "required": ["wave", "name", "execute_once", "trigger", "actions"],
      "properties": {
        "wave": { "type": "integer", "minimum": 0 },
        "name": { "type": "string" },
        "execute_once": { "type": "boolean" },
        "trigger": { "$ref": "#/$defs/waveTrigger" },
        "actions": {
          "type": "array",
          "items": { "$ref": "#/$defs/waveAction" }
        }
      }
    }
  }
}"""


def validate_script_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """校验脚本数据是否符合 Schema 定义"""
    schema = json.loads(_SCHEMA_JSON)
    validator = Draft202012Validator(schema)
    errors: list[dict[str, str]] = []
    for err in validator.iter_errors(data):
        path = "/"
        if err.absolute_path:
            path = "/" + "/".join(str(p) for p in err.absolute_path)
        errors.append({"path": path, "message": err.message})
    return errors


def assert_valid(data: dict[str, Any]) -> None:
    errs = validate_script_data(data)
    if errs:
        raise ValueError(f"Invalid script: {errs[0]!r}")
