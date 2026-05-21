"""日志动作处理器：处理记录日志信息的逻辑。"""

from __future__ import annotations

from nzfz_executor.actions.base import ActionHandler, ActionResult
from nzfz_executor.context import ExecutionContext


class LogActionHandler(ActionHandler):
    """日志动作处理器：执行记录日志信息的操作，用于脚本调试与运行追踪。"""

    action_type: str = "log"
    """动作类型标识符：记录日志"""

    def execute(self, context: ExecutionContext) -> ActionResult:
        """执行日志记录动作。

        Args:
            context: 执行上下文，包含窗口、截图等运行时信息。

        Returns:
            日志记录的执行结果。

        Raises:
            NotImplementedError: 当前尚未实现具体逻辑。
        """
        raise NotImplementedError

    def validate(self, action_data: dict) -> list[str]:
        """校验日志动作数据是否合法。

        Args:
            action_data: 待校验的动作数据字典，应包含日志消息内容。

        Returns:
            校验错误信息列表，空列表表示校验通过。
        """
        return []