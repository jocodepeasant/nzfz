"""单局日志与报告。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ActionLog:
    action_type: str
    action_name: str
    wave: int
    started_at: datetime
    finished_at: datetime | None = None
    success: bool | None = None
    retry_count: int = 0
    error_message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "wave": self.wave,
            "started_at": self.started_at.isoformat(),
            "retry_count": self.retry_count,
            "extra": self.extra,
        }
        if self.finished_at is not None:
            d["finished_at"] = self.finished_at.isoformat()
        if self.success is not None:
            d["success"] = self.success
        if self.error_message is not None:
            d["error_message"] = self.error_message
        return d


@dataclass
class RunReport:
    script_id: str
    script_name: str
    started_at: datetime
    finished_at: datetime | None = None
    result: str | None = None
    total_waves: int = 0
    actions: list[ActionLog] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_action(self, log: ActionLog) -> None:
        self.actions.append(log)

    def summary(self) -> dict[str, Any]:
        total = len(self.actions)
        success = sum(1 for a in self.actions if a.success is True)
        fail = sum(1 for a in self.actions if a.success is False)
        duration_seconds: float | None = None
        if self.finished_at is not None:
            duration_seconds = (self.finished_at - self.started_at).total_seconds()
        return {
            "total": total,
            "success": success,
            "fail": fail,
            "duration_seconds": duration_seconds,
        }

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "script_id": self.script_id,
            "script_name": self.script_name,
            "started_at": self.started_at.isoformat(),
            "total_waves": self.total_waves,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
        }
        if self.finished_at is not None:
            d["finished_at"] = self.finished_at.isoformat()
        if self.result is not None:
            d["result"] = self.result
        return d


def write_report(path: Path, report: RunReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
