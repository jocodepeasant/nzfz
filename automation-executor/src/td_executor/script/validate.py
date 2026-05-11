"""Validate script dict against the shared JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def _schema_path() -> Path:
    # automation-executor/src/td_executor/script/validate.py -> parents[4] = repo root
    here = Path(__file__).resolve()
    repo_root = here.parents[4]
    return repo_root / "schemas" / "tower_defense_script_v1.schema.json"


def validate_script_data(data: dict[str, Any]) -> list[dict[str, str]]:
    schema_file = _schema_path()
    if not schema_file.is_file():
        return [{"path": "/", "message": f"找不到 Schema 文件: {schema_file}"}]
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
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
