"""单局日志与报告管理。"""

from __future__ import annotations

import json
import time
import os
import datetime
from dataclasses import dataclass, asdict


@dataclass
class ActionRecord:
    action_type: str
    name: str
    result: str
    retry_count: int = 0
    elapsed_ms: int = 0
    detail: str = ""


class ReportManager:
    def __init__(self, script_id: str = "", report_dir: str = "."):
        self.script_id = script_id
        self.report_dir = report_dir
        self._records: list[ActionRecord] = []
        self._start_time: float = 0.0

    def record_action(
        self,
        action_type: str,
        name: str,
        result: str,
        retry_count: int = 0,
        elapsed_ms: int = 0,
        detail: str = "",
    ) -> None:
        self._records.append(
            ActionRecord(
                action_type=action_type,
                name=name,
                result=result,
                retry_count=retry_count,
                elapsed_ms=elapsed_ms,
                detail=detail,
            )
        )

    def start_run(self) -> None:
        self._start_time = time.time()

    def finish_run(self, outcome: str = "unknown") -> dict:
        end_time = time.time()
        start_dt = datetime.datetime.fromtimestamp(self._start_time)
        end_dt = datetime.datetime.fromtimestamp(end_time)
        success_count = sum(1 for r in self._records if r.result == "success")
        failed_count = sum(1 for r in self._records if r.result == "failed")
        skipped_count = sum(1 for r in self._records if r.result == "skipped")
        return {
            "script_id": self.script_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "elapsed_seconds": round(end_time - self._start_time, 3),
            "outcome": outcome,
            "total_actions": len(self._records),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "actions": [asdict(r) for r in self._records],
        }

    def save_report(self, report: dict, filename: str | None = None) -> str:
        os.makedirs(self.report_dir, exist_ok=True)
        if filename is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.script_id}_{ts}.json"
        filepath = os.path.join(self.report_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath

    def get_summary(self) -> str:
        success_count = sum(1 for r in self._records if r.result == "success")
        failed_count = sum(1 for r in self._records if r.result == "failed")
        skipped_count = sum(1 for r in self._records if r.result == "skipped")
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        lines = [
            f"脚本: {self.script_id}",
            f"总操作数: {len(self._records)}",
            f"成功: {success_count}  失败: {failed_count}  跳过: {skipped_count}",
            f"已耗时: {elapsed:.1f}s",
        ]
        return "\n".join(lines)
