"""P2-11 KeyboardController 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from nzfz_executor.core.actions.backends.dry_run_keyboard_backend import (
    DryRunKeyboardBackend,
)
from nzfz_executor.core.actions.backends.send_input_keyboard_backend import (
    SendInputKeyboardBackend,
)
from nzfz_executor.core.actions.keyboard_controller import KeyboardController
from nzfz_executor.core.actions.models import KeyPressAction
from nzfz_executor.core.models import ConnectedWindow, WindowRect


def _connected() -> ConnectedWindow:
    return ConnectedWindow(
        hwnd=1,
        title="Game",
        process_name="game.exe",
        pid=1,
        window_rect=WindowRect(0, 0, 800, 600),
        client_rect=WindowRect(0, 0, 800, 600),
    )


class TestKeyboardControllerFactory:
    def test_create_default_true_uses_dry_run_backend(self) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        assert isinstance(controller._backend, DryRunKeyboardBackend)

    def test_create_default_false_uses_send_input_backend(self) -> None:
        controller = KeyboardController.create_default(dry_run=False)
        assert isinstance(controller._backend, SendInputKeyboardBackend)


class TestKeyboardControllerPress:
    def test_dry_run_success(self) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        result = controller.press(
            KeyPressAction(key="1"),
            context=_connected(),
        )

        assert result.success is True
        assert "[Keyboard] dry-run press key=1" in result.message

    def test_empty_key_fails(self) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        result = controller.press(KeyPressAction(key=""), context=_connected())

        assert result.success is False
        assert "key 不能为空" in result.message

    def test_unsupported_key_fails(self) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        result = controller.press(KeyPressAction(key="f1"), context=_connected())

        assert result.success is False
        assert "不支持" in result.message

    def test_no_context_fails(self) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        result = controller.press(KeyPressAction(key="1"), context=None)

        assert result.success is False
        assert "未连接窗口" in result.message

    def test_foreground_warning_does_not_block(self, monkeypatch) -> None:
        controller = KeyboardController.create_default(dry_run=True)
        monkeypatch.setattr(
            "nzfz_executor.core.actions.keyboard_controller.warn_if_not_foreground",
            lambda context, log: log("[Safety][Warning] not foreground"),
        )
        logs: list[str] = []
        result = controller.press(
            KeyPressAction(key="o"),
            context=_connected(),
            log=logs.append,
        )

        assert result.success is True
        assert any("[Safety][Warning]" in line for line in logs)

    def test_real_press_calls_backend(self) -> None:
        backend = MagicMock()
        controller = KeyboardController(backend=backend, dry_run=False)
        result = controller.press(
            KeyPressAction(key="O"),
            context=_connected(),
        )

        assert result.success is True
        backend.press.assert_called_once_with("o", hold_ms=0)
