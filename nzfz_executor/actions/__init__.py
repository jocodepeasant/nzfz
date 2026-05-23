"""动作处理器包：提供动作处理器基类、注册表与执行结果定义。"""

from nzfz_executor.actions.base import ActionHandler, ActionRegistry, ActionResult
from nzfz_executor.actions.log import LogActionHandler
from nzfz_executor.actions.pan import PanToRegionHandler
from nzfz_executor.actions.place import PlaceTrapHandler
from nzfz_executor.actions.remove import RemoveTrapHandler
from nzfz_executor.actions.upgrade import UpgradeTrapHandler

__all__ = [
    "ActionHandler",
    "ActionRegistry",
    "ActionResult",
    "register_builtin_handlers",
]


def register_builtin_handlers() -> None:
    """注册内置动作处理器。"""
    ActionRegistry.register(LogActionHandler)
    ActionRegistry.register(PlaceTrapHandler)
    ActionRegistry.register(UpgradeTrapHandler)
    ActionRegistry.register(RemoveTrapHandler)
    ActionRegistry.register(PanToRegionHandler)
