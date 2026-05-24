"""P1-05 feedback 模块测试。"""

from __future__ import annotations

import pytest

from nzfz_executor.ui.feedback import (
    FeedbackCode,
    FeedbackLevel,
    get_feedback_level,
    get_feedback_message,
    get_feedback_text,
)


class TestFeedbackMessages:
    def test_get_existing_code(self) -> None:
        message = get_feedback_message(FeedbackCode.SEARCH_INPUT_REQUIRED)
        assert message.level == FeedbackLevel.INFO
        assert "请输入" in message.text

    def test_get_feedback_text(self) -> None:
        text = get_feedback_text(FeedbackCode.SEARCH_FOUND, count=3)
        assert text == "找到 3 个窗口"

    def test_format_missing_kwargs_no_exception(self) -> None:
        text = get_feedback_text(FeedbackCode.SEARCH_FOUND)
        assert text == "找到 {count} 个窗口"

    def test_get_feedback_level(self) -> None:
        assert get_feedback_level(FeedbackCode.CONNECT_TIMEOUT) == FeedbackLevel.ERROR
        assert get_feedback_level(FeedbackCode.HEALTH_TIMEOUT) == FeedbackLevel.WARNING

    def test_unknown_code_fallback(self) -> None:
        from nzfz_executor.ui.feedback import messages as mod

        saved = mod.FEEDBACK_MESSAGES.pop(FeedbackCode.SEARCH_INPUT_REQUIRED)
        try:
            message = get_feedback_message(FeedbackCode.SEARCH_INPUT_REQUIRED)
            assert message.level == FeedbackLevel.ERROR
            assert "未知错误" in message.text
        finally:
            mod.FEEDBACK_MESSAGES[FeedbackCode.SEARCH_INPUT_REQUIRED] = saved
