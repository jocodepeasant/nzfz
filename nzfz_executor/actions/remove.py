"""移除陷阱动作处理器：处理从地图上移除已放置陷阱的逻辑。"""

from __future__ import annotations

from nzfz_executor.actions.base import ActionHandler, ActionResult
from nzfz_executor.context import ExecutionContext


class RemoveTrapHandler(ActionHandler):
    """移除陷阱动作处理器：执行从游戏地图上移除已放置陷阱的操作。"""

    action_type: str = "remove_trap"
    """动作类型标识符：移除陷阱"""

    def execute(self, context: ExecutionContext) -> ActionResult:
        """执行移除陷阱动作。

        Args:
            context: 执行上下文，包含窗口、截图等运行时信息。

        Returns:
            移除陷阱的执行结果。

        Raises:
            NotImplementedError: 当前尚未实现具体逻辑。
        """
        raise NotImplementedError

    def validate(self, action_data: dict) -> list[str]:
        """校验移除陷阱动作数据是否合法。

        Args:
            action_data: 待校验的动作数据字典，应包含待移除陷阱的位置信息。

        Returns:
            校验错误信息列表，空列表表示校验通过。
        """
        return []