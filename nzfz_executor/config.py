"""全局配置管理：定义执行器的运行参数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExecutorConfig:
    """执行器全局配置。"""

    schema_path: Path = field(default_factory=lambda: Path("schemas/tower_defense_script_v1.schema.json"))
    max_run_minutes: int = 60
    default_action_timeout_ms: int = 5000
    default_retry_count: int = 3
    default_resource_policy: str = "wait"
    default_wait_resource_timeout_ms: int = 30000
    wait_after_pan_ms: int = 800
    wait_after_place_ms: int = 600
    wait_after_remove_ms: int = 600
    wait_after_upgrade_ms: int = 1000
    reset_view_on_retry: bool = False
    capture_backend: str = "mss"
    title_keyword: str = "逆战"
    reports_dir: Path = field(default_factory=lambda: Path("reports"))
    templates_dir: Path = field(default_factory=lambda: Path("assets/templates"))

    @classmethod
    def from_script_runtime(cls, runtime: dict[str, Any]) -> ExecutorConfig:
        """从脚本 runtime 字段构建配置。"""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutorConfig:
        """从字典构建配置。"""
        raise NotImplementedError