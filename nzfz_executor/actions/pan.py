"""视角平移动作处理器：处理将游戏视角平移至指定区域的逻辑。"""

from __future__ import annotations

from nzfz_executor.actions.base import ActionHandler, ActionResult
from nzfz_executor.context import ExecutionContext


class PanToRegionHandler(ActionHandler):
    """视角平移动作处理器：执行将游戏视角平移至指定区域的操作。"""

    action_type: str = "pan_to_region"
    """动作类型标识符：视角平移至区域"""

    def execute(self, context: ExecutionContext) -> ActionResult:
        """执行视角平移动作。

        Args:
            context: 执行上下文，包含窗口、截图等运行时信息。

        Returns:
            视角平移的执行结果。

        Raises:
            NotImplementedError: 当前尚未实现具体逻辑。
        """
        raise NotImplementedError

    def validate(self, action_data: dict) -> list[str]:
        """校验视角平移动作数据是否合法。

        Args:
            action_data: 待校验的动作数据字典，应包含目标区域标识或坐标信息。

        Returns:
            校验错误信息列表，空列表表示校验通过。
        """
        return []