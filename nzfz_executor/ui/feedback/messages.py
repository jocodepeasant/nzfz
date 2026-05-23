"""用户反馈提示码、级别与标准文案。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeedbackLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class FeedbackCode(Enum):
    SEARCH_INPUT_REQUIRED = "search.input_required"
    SEARCHING = "search.searching"
    SEARCH_NO_RESULT = "search.no_result"
    SEARCH_FOUND = "search.found"
    SEARCH_FAILED = "search.failed"
    SEARCH_TIMEOUT = "search.timeout"

    CONNECTING = "connect.connecting"
    CONNECT_SUCCESS_READY = "connect.success_ready"
    CONNECT_FAILED = "connect.failed"
    CONNECT_TIMEOUT = "connect.timeout"
    CONNECT_EXCEPTION = "connect.exception"
    DISCONNECTED = "connect.disconnected"
    DISCONNECT_SUCCESS = "connect.disconnect_success"

    HEALTH_READY = "health.ready"
    HEALTH_NOT_READY_FOREGROUND = "health.not_ready_foreground"
    HEALTH_UNHEALTHY = "health.unhealthy"
    HEALTH_TIMEOUT = "health.timeout"
    HEALTH_EXCEPTION = "health.exception"
    HEALTH_DISCONNECTED = "health.disconnected"

    WINDOW_MINIMIZED = "window.minimized"
    WINDOW_NOT_FOREGROUND = "window.not_foreground"
    WINDOW_INVALID = "window.invalid"
    WINDOW_PROCESS_EXITED = "window.process_exited"
    WINDOW_INVISIBLE = "window.invisible"

    CONFIRM_SWITCH_CONNECTION_TITLE = "confirm.switch_connection.title"
    CONFIRM_SWITCH_CONNECTION_MESSAGE = "confirm.switch_connection.message"

    TASK_EXCEPTION = "task.exception"
    TASK_RESULT_EXPIRED = "task.result_expired"


@dataclass(frozen=True)
class FeedbackMessage:
    level: FeedbackLevel
    text: str


FEEDBACK_MESSAGES: dict[FeedbackCode, FeedbackMessage] = {
    FeedbackCode.SEARCH_INPUT_REQUIRED: FeedbackMessage(
        FeedbackLevel.INFO,
        "请输入窗口标题、进程名或 PID",
    ),
    FeedbackCode.SEARCHING: FeedbackMessage(
        FeedbackLevel.INFO,
        "正在搜索窗口...",
    ),
    FeedbackCode.SEARCH_NO_RESULT: FeedbackMessage(
        FeedbackLevel.WARNING,
        "未找到匹配窗口",
    ),
    FeedbackCode.SEARCH_FOUND: FeedbackMessage(
        FeedbackLevel.SUCCESS,
        "找到 {count} 个窗口",
    ),
    FeedbackCode.SEARCH_FAILED: FeedbackMessage(
        FeedbackLevel.ERROR,
        "搜索窗口失败，请稍后重试",
    ),
    FeedbackCode.SEARCH_TIMEOUT: FeedbackMessage(
        FeedbackLevel.ERROR,
        "搜索窗口超时，请稍后重试",
    ),
    FeedbackCode.CONNECTING: FeedbackMessage(
        FeedbackLevel.INFO,
        "正在连接窗口...",
    ),
    FeedbackCode.CONNECT_SUCCESS_READY: FeedbackMessage(
        FeedbackLevel.SUCCESS,
        "已连接，执行就绪",
    ),
    FeedbackCode.CONNECT_FAILED: FeedbackMessage(
        FeedbackLevel.ERROR,
        "连接窗口失败，请检查窗口状态后重试",
    ),
    FeedbackCode.CONNECT_TIMEOUT: FeedbackMessage(
        FeedbackLevel.ERROR,
        "连接窗口超时，请稍后重试",
    ),
    FeedbackCode.CONNECT_EXCEPTION: FeedbackMessage(
        FeedbackLevel.ERROR,
        "连接窗口异常，请稍后重试",
    ),
    FeedbackCode.DISCONNECTED: FeedbackMessage(
        FeedbackLevel.INFO,
        "未连接游戏窗口",
    ),
    FeedbackCode.DISCONNECT_SUCCESS: FeedbackMessage(
        FeedbackLevel.INFO,
        "已断开连接",
    ),
    FeedbackCode.HEALTH_READY: FeedbackMessage(
        FeedbackLevel.SUCCESS,
        "执行就绪",
    ),
    FeedbackCode.HEALTH_NOT_READY_FOREGROUND: FeedbackMessage(
        FeedbackLevel.WARNING,
        "窗口未在前台，请切回游戏窗口",
    ),
    FeedbackCode.HEALTH_UNHEALTHY: FeedbackMessage(
        FeedbackLevel.ERROR,
        "窗口状态异常，请检查游戏窗口",
    ),
    FeedbackCode.HEALTH_TIMEOUT: FeedbackMessage(
        FeedbackLevel.WARNING,
        "窗口状态检测超时",
    ),
    FeedbackCode.HEALTH_EXCEPTION: FeedbackMessage(
        FeedbackLevel.WARNING,
        "窗口状态检测失败",
    ),
    FeedbackCode.HEALTH_DISCONNECTED: FeedbackMessage(
        FeedbackLevel.INFO,
        "执行未就绪",
    ),
    FeedbackCode.WINDOW_MINIMIZED: FeedbackMessage(
        FeedbackLevel.WARNING,
        "窗口已最小化，请恢复窗口后重试",
    ),
    FeedbackCode.WINDOW_NOT_FOREGROUND: FeedbackMessage(
        FeedbackLevel.WARNING,
        "窗口未在前台，请切回游戏窗口",
    ),
    FeedbackCode.WINDOW_INVALID: FeedbackMessage(
        FeedbackLevel.ERROR,
        "窗口已失效，请重新搜索",
    ),
    FeedbackCode.WINDOW_PROCESS_EXITED: FeedbackMessage(
        FeedbackLevel.ERROR,
        "游戏进程已退出，请重新启动游戏",
    ),
    FeedbackCode.WINDOW_INVISIBLE: FeedbackMessage(
        FeedbackLevel.ERROR,
        "游戏窗口不可见，请检查窗口状态",
    ),
    FeedbackCode.CONFIRM_SWITCH_CONNECTION_TITLE: FeedbackMessage(
        FeedbackLevel.WARNING,
        "切换连接窗口",
    ),
    FeedbackCode.CONFIRM_SWITCH_CONNECTION_MESSAGE: FeedbackMessage(
        FeedbackLevel.WARNING,
        "当前已连接其他窗口。继续操作将断开当前连接，并连接所选窗口。是否继续？",
    ),
    FeedbackCode.TASK_EXCEPTION: FeedbackMessage(
        FeedbackLevel.ERROR,
        "任务执行异常，请稍后重试",
    ),
    FeedbackCode.TASK_RESULT_EXPIRED: FeedbackMessage(
        FeedbackLevel.INFO,
        "任务结果已过期，已忽略",
    ),
}


def get_feedback_message(code: FeedbackCode) -> FeedbackMessage:
    return FEEDBACK_MESSAGES.get(
        code,
        FeedbackMessage(
            FeedbackLevel.ERROR,
            "发生未知错误，请稍后重试",
        ),
    )


def get_feedback_text(code: FeedbackCode, **kwargs: object) -> str:
    message = get_feedback_message(code)

    try:
        return message.text.format(**kwargs)
    except Exception:
        return message.text


def get_feedback_level(code: FeedbackCode) -> FeedbackLevel:
    return get_feedback_message(code).level
