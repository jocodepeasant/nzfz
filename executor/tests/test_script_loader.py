"""P2-10 ScriptLoader 测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nzfz_executor.core.scripts import ScriptLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPT = REPO_ROOT / "resources" / "scripts" / "default_script.json"


def test_load_default_script_success() -> None:
    result = ScriptLoader().load(DEFAULT_SCRIPT)

    assert result.success is True
    assert result.script is not None
    assert result.indexes is not None
    assert result.script.schema_version == "1.1.0"
    assert result.script.compatibility.profile == "tower_defense_v1_basic"
    assert len(result.errors) == 0


def test_load_missing_script_fails() -> None:
    result = ScriptLoader().load(REPO_ROOT / "resources/scripts/not_exists.json")

    assert result.success is False
    assert "不存在" in result.errors[0]


def test_load_invalid_schema_version(tmp_path: Path) -> None:
    script_path = tmp_path / "bad_schema.json"
    data = json.loads(DEFAULT_SCRIPT.read_text(encoding="utf-8"))
    data["schema_version"] = "1.0.0"
    script_path.write_text(json.dumps(data), encoding="utf-8")

    result = ScriptLoader().load(script_path)

    assert result.success is False
    assert any("schema_version" in error for error in result.errors)


def test_load_unsupported_required_capability(tmp_path: Path) -> None:
    script_path = tmp_path / "bad_caps.json"
    data = json.loads(DEFAULT_SCRIPT.read_text(encoding="utf-8"))
    data["compatibility"]["required_capabilities"] = ["script_load", "wave_ocr"]
    script_path.write_text(json.dumps(data), encoding="utf-8")

    result = ScriptLoader().load(script_path)

    assert result.success is False
    assert any("wave_ocr" in error for error in result.errors)


def test_load_enabled_upgrade_trap_fails(tmp_path: Path) -> None:
    script_path = tmp_path / "bad_upgrade.json"
    data = json.loads(DEFAULT_SCRIPT.read_text(encoding="utf-8"))
    data["waves"][0]["actions"].append(
        {
            "action_id": "w1_bad_upgrade",
            "type": "upgrade_trap",
            "enabled": True,
            "name": "bad",
        },
    )
    script_path.write_text(json.dumps(data), encoding="utf-8")

    result = ScriptLoader().load(script_path)

    assert result.success is False
    assert any("upgrade_trap" in error for error in result.errors)


def test_load_disabled_upgrade_trap_success(tmp_path: Path) -> None:
    result = ScriptLoader().load(DEFAULT_SCRIPT)

    assert result.success is True
    assert any(
        "disabled action" in warning and "upgrade_trap" in warning
        for warning in result.warnings
    )
