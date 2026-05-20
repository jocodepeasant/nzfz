"""动作处理器包：提供动作处理器基类、注册表与执行结果定义。"""

from nzfz_executor.actions.base import ActionHandler, ActionRegistry, ActionResult

__all__ = [
    "ActionHandler",
    "ActionRegistry",
    "ActionResult",
]