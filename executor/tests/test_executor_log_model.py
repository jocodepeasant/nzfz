"""P2-06 执行器日志模型测试。"""

from __future__ import annotations

from datetime import datetime

from nzfz_executor.ui.config.defaults import DEFAULT_EXECUTOR_LOG_TIME_FORMAT
from nzfz_executor.ui.models.executor_log import ExecutorLogEntry, ExecutorLogLevel


class TestExecutorLogModel:
    def test_log_level_values(self) -> None:
        assert ExecutorLogLevel.INFO.value == "info"
        assert ExecutorLogLevel.SUCCESS.value == "success"
        assert ExecutorLogLevel.ERROR.value == "error"

    def test_log_entry_fields(self) -> None:
        ts = datetime(2026, 1, 1, 12, 30, 45)
        entry = ExecutorLogEntry(
            timestamp=ts,
            level=ExecutorLogLevel.INFO,
            message="测试消息",
            execution_id=7,
            step="step-1",
        )
        assert entry.timestamp == ts
        assert entry.level == ExecutorLogLevel.INFO
        assert entry.message == "测试消息"
        assert entry.execution_id == 7
        assert entry.step == "step-1"

    def test_format_log_entry_pattern(self) -> None:
        entry = ExecutorLogEntry(
            timestamp=datetime(2026, 1, 1, 0, 3, 1),
            level=ExecutorLogLevel.INFO,
            message="准备启动执行任务",
        )
        timestamp = entry.timestamp.strftime(DEFAULT_EXECUTOR_LOG_TIME_FORMAT)
        level = entry.level.value.upper()
        formatted = f"[{timestamp}] [{level}] {entry.message}"
        assert formatted == "[00:03:01] [INFO] 准备启动执行任务"
