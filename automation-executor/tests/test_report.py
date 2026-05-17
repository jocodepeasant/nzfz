from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from td_executor.engine.report import ActionLog, RunReport, write_report


class TestActionLog:
    def test_create_with_defaults(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        log = ActionLog(action_type="place_trap", action_name="放置减速", wave=1, started_at=now)
        assert log.action_type == "place_trap"
        assert log.action_name == "放置减速"
        assert log.wave == 1
        assert log.started_at == now
        assert log.finished_at is None
        assert log.success is None
        assert log.retry_count == 0
        assert log.error_message is None
        assert log.extra == {}

    def test_create_with_all_fields(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        later = now + timedelta(seconds=5)
        log = ActionLog(
            action_type="place_trap",
            action_name="放置减速",
            wave=1,
            started_at=now,
            finished_at=later,
            success=True,
            retry_count=1,
            error_message=None,
            extra={"slot_id": "A01"},
        )
        assert log.finished_at == later
        assert log.success is True
        assert log.retry_count == 1
        assert log.extra == {"slot_id": "A01"}

    def test_to_dict_minimal(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        log = ActionLog(action_type="log", action_name="消息", wave=2, started_at=now)
        d = log.to_dict()
        assert d["action_type"] == "log"
        assert d["action_name"] == "消息"
        assert d["wave"] == 2
        assert d["started_at"] == "2026-01-01T12:00:00"
        assert d["retry_count"] == 0
        assert d["extra"] == {}
        assert "finished_at" not in d
        assert "success" not in d
        assert "error_message" not in d

    def test_to_dict_full(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        later = now + timedelta(seconds=3)
        log = ActionLog(
            action_type="upgrade_trap",
            action_name="升级输出",
            wave=2,
            started_at=now,
            finished_at=later,
            success=False,
            retry_count=2,
            error_message="资源不足",
            extra={"trap_id": "damage_trap"},
        )
        d = log.to_dict()
        assert d["finished_at"] == later.isoformat()
        assert d["success"] is False
        assert d["error_message"] == "资源不足"


class TestRunReport:
    def test_create_with_defaults(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试脚本", started_at=now)
        assert report.script_id == "v1"
        assert report.script_name == "测试脚本"
        assert report.started_at == now
        assert report.finished_at is None
        assert report.result is None
        assert report.total_waves == 0
        assert report.actions == []
        assert report.metadata == {}

    def test_add_action(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        log = ActionLog(action_type="place_trap", action_name="放置", wave=1, started_at=now)
        report.add_action(log)
        assert len(report.actions) == 1
        assert report.actions[0] is log

    def test_add_multiple_actions(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        for i in range(3):
            report.add_action(ActionLog(action_type="log", action_name=f"动作{i}", wave=1, started_at=now))
        assert len(report.actions) == 3

    def test_summary_empty(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        s = report.summary()
        assert s["total"] == 0
        assert s["success"] == 0
        assert s["fail"] == 0
        assert s["duration_seconds"] is None

    def test_summary_with_actions(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        later = now + timedelta(minutes=5)
        report = RunReport(script_id="v1", script_name="测试", started_at=now, finished_at=later, result="win")
        report.add_action(ActionLog(action_type="place_trap", action_name="a1", wave=1, started_at=now, success=True))
        report.add_action(ActionLog(action_type="upgrade_trap", action_name="a2", wave=2, started_at=now, success=False))
        report.add_action(ActionLog(action_type="log", action_name="a3", wave=2, started_at=now))
        s = report.summary()
        assert s["total"] == 3
        assert s["success"] == 1
        assert s["fail"] == 1
        assert s["duration_seconds"] == 300.0

    def test_to_dict_minimal(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        d = report.to_dict()
        assert d["script_id"] == "v1"
        assert d["script_name"] == "测试"
        assert d["started_at"] == "2026-01-01T12:00:00"
        assert d["total_waves"] == 0
        assert d["actions"] == []
        assert d["metadata"] == {}
        assert "finished_at" not in d
        assert "result" not in d

    def test_to_dict_full(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        later = now + timedelta(minutes=10)
        report = RunReport(
            script_id="v1",
            script_name="测试",
            started_at=now,
            finished_at=later,
            result="win",
            total_waves=5,
            metadata={"author": "test"},
        )
        log = ActionLog(action_type="place_trap", action_name="放置", wave=1, started_at=now, success=True)
        report.add_action(log)
        d = report.to_dict()
        assert d["finished_at"] == later.isoformat()
        assert d["result"] == "win"
        assert d["total_waves"] == 5
        assert d["metadata"] == {"author": "test"}
        assert len(d["actions"]) == 1
        assert d["actions"][0]["action_type"] == "place_trap"


class TestWriteReport:
    def test_write_creates_file(self, tmp_path: Path) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        out = tmp_path / "report.json"
        write_report(out, report)
        assert out.is_file()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["script_id"] == "v1"
        assert data["started_at"] == "2026-01-01T12:00:00"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now)
        out = tmp_path / "deep" / "nested" / "report.json"
        write_report(out, report)
        assert out.is_file()

    def test_write_with_actions(self, tmp_path: Path) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="测试", started_at=now, result="win")
        report.add_action(ActionLog(action_type="place_trap", action_name="放置", wave=1, started_at=now, success=True))
        out = tmp_path / "report.json"
        write_report(out, report)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data["actions"]) == 1
        assert data["actions"][0]["success"] is True
        assert data["result"] == "win"

    def test_write_utf8_content(self, tmp_path: Path) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        report = RunReport(script_id="v1", script_name="空间站脚本", started_at=now, metadata={"描述": "中文测试"})
        out = tmp_path / "report.json"
        write_report(out, report)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["script_name"] == "空间站脚本"
        assert data["metadata"]["描述"] == "中文测试"
