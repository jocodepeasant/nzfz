"""日志动作处理器：处理记录日志信息的逻辑。"""

from __future__ import annotations

import logging

from nzfz_executor.actions.base import ActionHandler, ActionResult
from nzfz_executor.context import ExecutionContext

logger = logging.getLogger(__name__)


class LogActionHandler(ActionHandler):
    """日志动作处理器：执行记录日志信息的操作，用于脚本调试与运行追踪。"""

    action_type: str = "log"

    def execute(self, context: ExecutionContext) -> ActionResult:
        message = context.action_data.get("message", "")
        logger.info("脚本日志: %s", message)
        return ActionResult(success=True, data=message)

    def validate(self, action_data: dict) -> list[str]:
        if not action_data.get("message"):
            return ["log 动作缺少 message 字段"]
        return []
