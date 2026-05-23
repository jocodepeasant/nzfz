"""脚本校验器模块，负责对脚本数据进行格式与规则校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from nzfz_executor.config import ExecutorConfig
from nzfz_executor.errors import ScriptValidationError


class ScriptValidator:
    """脚本校验器，用于校验脚本数据是否符合预定义的 Schema 规范。"""

    def __init__(self, schema_path: Path | None = None) -> None:
        self.schema_path: Path | None = schema_path

    def _resolve_schema_path(self) -> Path:
        if self.schema_path is not None:
            return self.schema_path
        return ExecutorConfig().schema_path

    def validate(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """校验脚本数据，返回错误列表。"""
        schema_file = self._resolve_schema_path()
        if not schema_file.is_file():
            return [{"path": "/", "message": f"Schema 文件不存在: {schema_file}"}]

        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [{"path": "/", "message": f"无法读取 Schema: {exc}"}]

        validator = Draft202012Validator(schema)
        errors: list[dict[str, str]] = []
        for err in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
            path = "/" + "/".join(str(part) for part in err.path) if err.path else "/"
            errors.append({"path": path, "message": err.message})
        return errors

    def assert_valid(self, data: dict[str, Any]) -> None:
        """断言脚本数据合法，校验失败时抛出异常。"""
        errors = self.validate(data)
        if errors:
            raise ScriptValidationError(errors)
