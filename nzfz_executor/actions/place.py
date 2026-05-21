"""放置陷阱动作处理器：处理在指定位置放置陷阱的逻辑。"""

from __future__ import annotations

from nzfz_executor.actions.base import ActionHandler, ActionResult
from nzfz_executor.context import ExecutionContext


class PlaceTrapHandler(ActionHandler):
    """放置陷阱动作处理器：执行在游戏地图指定坐标放置陷阱的操作。"""

    action_type: str = "place_trap"
    """动作类型标识符：放置陷阱"""

    def execute(self, context: ExecutionContext) -> ActionResult:
        """执行放置陷阱动作。

        Args:
            context: 执行上下文，包含窗口、截图等运行时信息。

        Returns:
            放置陷阱的执行结果。

        Raises:
            NotImplementedError: 当前尚未实现具体逻辑。
        """
        raise NotImplementedError

    def validate(self, action_data: dict) -> list[str]:
        """校验放置陷阱动作数据是否合法。

        Args:
            action_data: 待校验的动作数据字典，应包含陷阱类型与坐标信息。

        Returns:
            校验错误信息列表，空列表表示校验通过。
        """
        return []