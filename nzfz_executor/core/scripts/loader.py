"""塔防脚本加载（P2-10）。"""

from __future__ import annotations

import json
from pathlib import Path

from nzfz_executor.core.scripts.indexes import build_script_indexes
from nzfz_executor.core.scripts.models import ScriptLoadResult
from nzfz_executor.core.scripts.parser import parse_script_definition
from nzfz_executor.core.scripts.validator import ScriptValidator


class ScriptLoader:
    """加载并校验塔防 script.json。"""

    def __init__(self, validator: ScriptValidator | None = None) -> None:
        self._validator = validator or ScriptValidator()

    def load(
        self,
        path: str | Path,
        *,
        strict_compatibility: bool = False,
    ) -> ScriptLoadResult:
        script_path = Path(path)

        if not script_path.is_file():
            return ScriptLoadResult(
                success=False,
                message=f"脚本文件不存在：{script_path}",
                errors=[f"脚本文件不存在：{script_path}"],
            )

        try:
            raw_text = script_path.read_text(encoding="utf-8")
        except OSError as exc:
            return ScriptLoadResult(
                success=False,
                message=f"读取脚本失败：{exc}",
                errors=[f"读取脚本失败：{exc}"],
            )

        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return ScriptLoadResult(
                success=False,
                message=f"JSON 解析失败：{exc}",
                errors=[f"JSON 解析失败：{exc}"],
            )

        if not isinstance(raw, dict):
            return ScriptLoadResult(
                success=False,
                message="脚本根节点必须是 JSON 对象",
                errors=["脚本根节点必须是 JSON 对象"],
            )

        try:
            script = parse_script_definition(raw)
        except (ValueError, TypeError, KeyError) as exc:
            return ScriptLoadResult(
                success=False,
                message=f"脚本结构解析失败：{exc}",
                errors=[f"脚本结构解析失败：{exc}"],
            )

        indexes, index_errors = build_script_indexes(script)
        if indexes is None:
            return ScriptLoadResult(
                success=False,
                script=script,
                message="脚本索引构建失败",
                errors=index_errors,
            )

        validation = self._validator.validate(
            script,
            indexes,
            strict_compatibility=strict_compatibility,
        )

        all_errors = list(index_errors) + list(validation.errors)
        if all_errors:
            return ScriptLoadResult(
                success=False,
                script=script,
                indexes=indexes,
                message="脚本校验失败",
                warnings=list(validation.warnings),
                errors=all_errors,
            )

        return ScriptLoadResult(
            success=True,
            script=script,
            indexes=indexes,
            message="脚本加载成功",
            warnings=list(validation.warnings),
        )
