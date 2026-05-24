"""键盘输入控制器（P2-11）。"""

from __future__ import annotations

from collections.abc import Callable

from nzfz_executor.core.actions.backends.dry_run_keyboard_backend import (
    DryRunKeyboardBackend,
)
from nzfz_executor.core.actions.backends.keyboard_base import KeyboardInputBackend
from nzfz_executor.core.actions.backends.send_input_keyboard_backend import (
    SendInputKeyboardBackend,
)
from nzfz_executor.core.actions.foreground import warn_if_not_foreground
from nzfz_executor.core.actions.key_utils import is_supported_key, normalize_key
from nzfz_executor.core.actions.models import ActionResult, KeyPressAction
from nzfz_executor.core.models import ConnectedWindow


class KeyboardController:
    """统一键盘输入入口。"""

    def __init__(
        self,
        backend: KeyboardInputBackend,
        dry_run: bool = True,
    ) -> None:
        self._backend = backend
        self._dry_run = dry_run

    @classmethod
    def create_default(cls, dry_run: bool = True) -> KeyboardController:
        backend: KeyboardInputBackend
        if dry_run:
            backend = DryRunKeyboardBackend()
        else:
            backend = SendInputKeyboardBackend()
        return cls(backend=backend, dry_run=dry_run)

    def press(
        self,
        action: KeyPressAction,
        context: ConnectedWindow | None = None,
        log: Callable[[str], None] | None = None,
    ) -> ActionResult:
        if not action.key.strip():
            return ActionResult(
                success=False,
                message="按键失败：key 不能为空",
            )

        normalized = normalize_key(action.key)
        if not is_supported_key(normalized):
            return ActionResult(
                success=False,
                message=f"按键失败：不支持的 key={action.key}",
            )

        if context is None:
            return ActionResult(
                success=False,
                message="按键失败：未连接窗口",
            )

        if context.hwnd <= 0:
            return ActionResult(
                success=False,
                message="按键失败：窗口句柄无效",
            )

        warn_if_not_foreground(context, log)

        hold_ms = max(0, action.hold_ms)
        if self._dry_run:
            return ActionResult(
                success=True,
                message=(
                    f"[Keyboard] dry-run press key={normalized} "
                    f"hold={hold_ms}ms"
                ),
            )

        try:
            self._backend.press(normalized, hold_ms=hold_ms)
            return ActionResult(
                success=True,
                message=(
                    f"[Keyboard] press key={normalized} hold={hold_ms}ms"
                ),
            )
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"按键异常：{exc}",
            )
