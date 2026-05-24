"""鼠标输入后端（P2-08）。"""

from nzfz_executor.core.actions.backends.base import MouseInputBackend
from nzfz_executor.core.actions.backends.dry_run_backend import DryRunMouseBackend
from nzfz_executor.core.actions.backends.send_input_backend import SendInputMouseBackend

__all__ = [
    "DryRunMouseBackend",
    "MouseInputBackend",
    "SendInputMouseBackend",
]
