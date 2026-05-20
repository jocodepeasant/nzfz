"""统一异常体系：定义执行器所有异常类型的层级结构。"""

from __future__ import annotations


class ExecutorError(Exception):
    """所有执行器异常的基类。"""

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


class ScriptLoadError(ExecutorError):
    """脚本加载失败异常。"""

    def __init__(self, path: str = "", message: str = "") -> None:
        self.path = path
        super().__init__(message or f"脚本加载失败: {path}")


class ScriptValidationError(ExecutorError):
    """脚本校验失败异常。"""

    def __init__(self, errors: list[dict[str, str]] | None = None, message: str = "") -> None:
        self.errors = errors or []
        super().__init__(message or f"脚本校验失败，共 {len(self.errors)} 项错误")


class ActionError(ExecutorError):
    """动作执行失败异常。"""

    def __init__(self, action_type: str = "", message: str = "") -> None:
        self.action_type = action_type
        super().__init__(message or f"动作执行失败: {action_type}")


class ConditionError(ExecutorError):
    """条件判断异常。"""

    def __init__(self, condition_type: str = "", message: str = "") -> None:
        self.condition_type = condition_type
        super().__init__(message or f"条件判断异常: {condition_type}")


class RetryExhaustedError(ExecutorError):
    """重试耗尽异常。"""

    def __init__(self, action_type: str = "", attempts: int = 0, message: str = "") -> None:
        self.action_type = action_type
        self.attempts = attempts
        super().__init__(message or f"重试耗尽: {action_type}，已尝试 {attempts} 次")


class ExecutorRuntimeError(ExecutorError):
    """运行时能力异常（窗口未找到、截图失败等）。"""

    def __init__(self, capability: str = "", message: str = "") -> None:
        self.capability = capability
        super().__init__(message or f"运行时能力异常: {capability}")