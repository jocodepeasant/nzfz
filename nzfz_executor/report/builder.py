"""报告构建器模块，定义动作日志、运行报告数据类及报告构建器。"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ActionLog:
    """动作日志，记录单个动作的执行详情。"""

    action_type: str
    """动作类型"""

    action_name: str
    """动作名称"""

    wave: int
    """所属波次"""

    started_at: datetime
    """动作开始时间"""

    finished_at: datetime | None = None
    """动作结束时间"""

    success: bool | None = None
    """是否执行成功"""

    retry_count: int = 0
    """重试次数"""

    error_message: str | None = None
    """错误信息"""

    extra: dict = field(default_factory=dict)
    """扩展信息"""

    def to_dict(self) -> dict:
        """将动作日志转换为字典。

        Returns:
            包含所有字段的字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError


@dataclass
class RunReport:
    """运行报告，记录一次脚本执行的完整信息。"""

    script_id: str
    """脚本标识"""

    script_name: str
    """脚本名称"""

    started_at: datetime
    """执行开始时间"""

    finished_at: datetime | None = None
    """执行结束时间"""

    result: str | None = None
    """执行结果"""

    total_waves: int = 0
    """总波次数"""

    actions: list[ActionLog] = field(default_factory=list)
    """动作日志列表"""

    metadata: dict = field(default_factory=dict)
    """元数据"""

    def add_action(self, log: ActionLog) -> None:
        """添加一条动作日志到报告中。

        Args:
            log: 动作日志实例
        """
        self.actions.append(log)

    def summary(self) -> dict:
        """生成运行报告摘要信息。

        Returns:
            包含摘要统计数据的字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """将运行报告转换为字典。

        Returns:
            包含所有字段的字典

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError


class ReportBuilder:
    """报告构建器，负责创建和持久化运行报告。"""

    def __init__(self, reports_dir: Path) -> None:
        """初始化报告构建器。

        Args:
            reports_dir: 报告文件存储目录
        """
        self.reports_dir: Path = reports_dir
        """报告文件存储目录"""

    def create_report(self, script_id: str, script_name: str) -> RunReport:
        """创建一份新的运行报告。

        Args:
            script_id: 脚本标识
            script_name: 脚本名称

        Returns:
            新创建的 RunReport 实例

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError

    def save_report(self, report: RunReport) -> Path:
        """将运行报告保存到文件。

        Args:
            report: 待保存的运行报告实例

        Returns:
            保存后的文件路径

        Raises:
            NotImplementedError: 该方法尚未实现
        """
        raise NotImplementedError