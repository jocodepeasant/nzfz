from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from td_executor.engine.retry import (
    ActionAbortedError,
    ActionResult,
    OnConditionFailedConfig,
    OnConditionFailedPolicy,
    OnFailConfig,
    OnFailPolicy,
    RetryConfig,
    RetryManager,
)


class TestOnConditionFailedPolicy:
    def test_wait_value(self) -> None:
        assert OnConditionFailedPolicy.WAIT.value == "wait"

    def test_skip_value(self) -> None:
        assert OnConditionFailedPolicy.SKIP.value == "skip"

    def test_from_string(self) -> None:
        assert OnConditionFailedPolicy("wait") == OnConditionFailedPolicy.WAIT
        assert OnConditionFailedPolicy("skip") == OnConditionFailedPolicy.SKIP


class TestOnFailPolicy:
    def test_skip_value(self) -> None:
        assert OnFailPolicy.SKIP.value == "skip"

    def test_abort_value(self) -> None:
        assert OnFailPolicy.ABORT.value == "abort"

    def test_from_string(self) -> None:
        assert OnFailPolicy("skip") == OnFailPolicy.SKIP
        assert OnFailPolicy("abort") == OnFailPolicy.ABORT


class TestRetryConfig:
    def test_defaults(self) -> None:
        cfg = RetryConfig()
        assert cfg.max_count == 0
        assert cfg.interval_ms == 0
        assert cfg.reset_view_before_retry is False
        assert cfg.micro_adjust_on_retry is False

    def test_from_dict_full(self) -> None:
        cfg = RetryConfig.from_dict({"max_count": 3, "interval_ms": 800, "reset_view_before_retry": True, "micro_adjust_on_retry": True})
        assert cfg.max_count == 3
        assert cfg.interval_ms == 800
        assert cfg.reset_view_before_retry is True
        assert cfg.micro_adjust_on_retry is True

    def test_from_dict_empty(self) -> None:
        cfg = RetryConfig.from_dict({})
        assert cfg.max_count == 0
        assert cfg.interval_ms == 0

    def test_from_dict_none(self) -> None:
        cfg = RetryConfig.from_dict(None)
        assert cfg.max_count == 0

    def test_from_dict_partial(self) -> None:
        cfg = RetryConfig.from_dict({"max_count": 5})
        assert cfg.max_count == 5
        assert cfg.interval_ms == 0


class TestOnConditionFailedConfig:
    def test_defaults(self) -> None:
        cfg = OnConditionFailedConfig()
        assert cfg.policy == OnConditionFailedPolicy.WAIT
        assert cfg.timeout_ms == 30000
        assert cfg.then == "retry_condition"

    def test_from_dict_skip(self) -> None:
        cfg = OnConditionFailedConfig.from_dict({"policy": "skip"})
        assert cfg.policy == OnConditionFailedPolicy.SKIP
        assert cfg.timeout_ms == 30000

    def test_from_dict_none(self) -> None:
        cfg = OnConditionFailedConfig.from_dict(None)
        assert cfg.policy == OnConditionFailedPolicy.WAIT

    def test_from_dict_custom_timeout(self) -> None:
        cfg = OnConditionFailedConfig.from_dict({"policy": "wait", "timeout_ms": 5000, "then": "retry_condition"})
        assert cfg.timeout_ms == 5000


class TestOnFailConfig:
    def test_defaults(self) -> None:
        cfg = OnFailConfig()
        assert cfg.policy == OnFailPolicy.SKIP

    def test_from_dict_abort(self) -> None:
        cfg = OnFailConfig.from_dict({"policy": "abort"})
        assert cfg.policy == OnFailPolicy.ABORT

    def test_from_dict_none(self) -> None:
        cfg = OnFailConfig.from_dict(None)
        assert cfg.policy == OnFailPolicy.SKIP


class TestActionResult:
    def test_success(self) -> None:
        r = ActionResult(success=True, attempts=1)
        assert r.success is True
        assert r.skipped is False
        assert r.attempts == 1
        assert r.data is None

    def test_failure_skipped(self) -> None:
        r = ActionResult(success=False, skipped=True, attempts=3)
        assert r.success is False
        assert r.skipped is True
        assert r.attempts == 3

    def test_with_data(self) -> None:
        r = ActionResult(success=True, attempts=1, data={"key": "value"})
        assert r.data == {"key": "value"}


class TestRetryManagerInit:
    def test_init_default(self) -> None:
        rm = RetryManager()
        assert rm._runtime_defaults == {}

    def test_init_with_defaults(self) -> None:
        defaults = {"default_retry_count": 2, "reset_view_on_retry": True}
        rm = RetryManager(runtime_defaults=defaults)
        assert rm._runtime_defaults == defaults


class TestResolveRetryConfig:
    def test_action_overrides_runtime(self) -> None:
        rm = RetryManager(runtime_defaults={"default_retry_count": 2, "reset_view_on_retry": True})
        cfg = rm.resolve_retry_config({"max_count": 3, "interval_ms": 800})
        assert cfg.max_count == 3
        assert cfg.interval_ms == 800
        assert cfg.reset_view_before_retry is True

    def test_none_uses_runtime_defaults(self) -> None:
        rm = RetryManager(runtime_defaults={"default_retry_count": 2, "reset_view_on_retry": True})
        cfg = rm.resolve_retry_config(None)
        assert cfg.max_count == 2
        assert cfg.reset_view_before_retry is True

    def test_no_runtime_defaults(self) -> None:
        rm = RetryManager()
        cfg = rm.resolve_retry_config(None)
        assert cfg.max_count == 0
        assert cfg.reset_view_before_retry is False

    def test_action_partial_with_runtime(self) -> None:
        rm = RetryManager(runtime_defaults={"default_retry_count": 5, "reset_view_on_retry": True})
        cfg = rm.resolve_retry_config({"interval_ms": 500})
        assert cfg.max_count == 5
        assert cfg.interval_ms == 500
        assert cfg.reset_view_before_retry is True


class TestResolveOnConditionFailed:
    def test_action_config(self) -> None:
        rm = RetryManager()
        cfg = rm.resolve_on_condition_failed({"policy": "skip"})
        assert cfg.policy == OnConditionFailedPolicy.SKIP

    def test_none_uses_runtime_defaults(self) -> None:
        rm = RetryManager(runtime_defaults={"default_resource_policy": "wait", "default_wait_resource_timeout_ms": 5000})
        cfg = rm.resolve_on_condition_failed(None)
        assert cfg.policy == OnConditionFailedPolicy.WAIT
        assert cfg.timeout_ms == 5000

    def test_no_runtime_defaults(self) -> None:
        rm = RetryManager()
        cfg = rm.resolve_on_condition_failed(None)
        assert cfg.policy == OnConditionFailedPolicy.WAIT
        assert cfg.timeout_ms == 30000


class TestResolveOnFail:
    def test_action_config(self) -> None:
        rm = RetryManager()
        cfg = rm.resolve_on_fail({"policy": "abort"})
        assert cfg.policy == OnFailPolicy.ABORT

    def test_none(self) -> None:
        rm = RetryManager()
        cfg = rm.resolve_on_fail(None)
        assert cfg.policy == OnFailPolicy.SKIP


class TestWaitForCondition:
    def test_skip_returns_immediately(self) -> None:
        rm = RetryManager()
        config = OnConditionFailedConfig(policy=OnConditionFailedPolicy.SKIP)
        result = rm.wait_for_condition(lambda: True, config)
        assert result is False

    def test_wait_succeeds_immediately(self) -> None:
        rm = RetryManager()
        config = OnConditionFailedConfig(policy=OnConditionFailedPolicy.WAIT, timeout_ms=5000)
        result = rm.wait_for_condition(lambda: True, config)
        assert result is True

    def test_wait_succeeds_after_polls(self) -> None:
        rm = RetryManager()
        call_count = 0
        def condition():
            nonlocal call_count
            call_count += 1
            return call_count >= 3
        config = OnConditionFailedConfig(policy=OnConditionFailedPolicy.WAIT, timeout_ms=5000)
        result = rm.wait_for_condition(condition, config)
        assert result is True
        assert call_count >= 3

    def test_wait_timeout_returns_false(self) -> None:
        rm = RetryManager()
        config = OnConditionFailedConfig(policy=OnConditionFailedPolicy.WAIT, timeout_ms=100, then="skip")
        result = rm.wait_for_condition(lambda: False, config)
        assert result is False

    def test_wait_timeout_retry_condition_final_check(self) -> None:
        rm = RetryManager()
        config = OnConditionFailedConfig(policy=OnConditionFailedPolicy.WAIT, timeout_ms=100, then="retry_condition")
        result = rm.wait_for_condition(lambda: False, config)
        assert result is False


class TestExecuteWithRetry:
    def test_first_attempt_success(self) -> None:
        rm = RetryManager()
        result = rm.execute_with_retry(
            action_fn=lambda: "ok",
            verify_fn=lambda r: r == "ok",
            retry_config=RetryConfig(max_count=2),
        )
        assert result.success is True
        assert result.attempts == 1
        assert result.data == "ok"

    def test_retry_then_success(self) -> None:
        rm = RetryManager()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            return "ok" if call_count >= 3 else "fail"
        def verify(r):
            return r == "ok"
        result = rm.execute_with_retry(
            action_fn=action,
            verify_fn=verify,
            retry_config=RetryConfig(max_count=3),
        )
        assert result.success is True
        assert result.attempts == 3

    def test_max_count_zero_no_retry(self) -> None:
        rm = RetryManager()
        result = rm.execute_with_retry(
            action_fn=lambda: "fail",
            verify_fn=lambda r: False,
            retry_config=RetryConfig(max_count=0),
            on_fail_config=OnFailConfig(policy=OnFailPolicy.SKIP),
        )
        assert result.success is False
        assert result.skipped is True
        assert result.attempts == 1

    def test_reset_view_callback(self) -> None:
        rm = RetryManager()
        reset_fn = MagicMock()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            return "ok" if call_count >= 2 else "fail"
        result = rm.execute_with_retry(
            action_fn=action,
            verify_fn=lambda r: r == "ok",
            retry_config=RetryConfig(max_count=2, reset_view_before_retry=True),
            reset_view_fn=reset_fn,
        )
        assert result.success is True
        reset_fn.assert_called_once()

    def test_micro_adjust_callback(self) -> None:
        rm = RetryManager()
        adjust_fn = MagicMock()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            return "ok" if call_count >= 2 else "fail"
        result = rm.execute_with_retry(
            action_fn=action,
            verify_fn=lambda r: r == "ok",
            retry_config=RetryConfig(max_count=2, micro_adjust_on_retry=True),
            micro_adjust_fn=adjust_fn,
        )
        assert result.success is True
        adjust_fn.assert_called_once()

    def test_action_exception_triggers_retry(self) -> None:
        rm = RetryManager()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("test error")
            return "ok"
        result = rm.execute_with_retry(
            action_fn=action,
            verify_fn=lambda r: r == "ok",
            retry_config=RetryConfig(max_count=2),
        )
        assert result.success is True
        assert result.attempts == 2

    def test_all_retries_exhausted_skip(self) -> None:
        rm = RetryManager()
        result = rm.execute_with_retry(
            action_fn=lambda: "fail",
            verify_fn=lambda r: False,
            retry_config=RetryConfig(max_count=2),
            on_fail_config=OnFailConfig(policy=OnFailPolicy.SKIP),
        )
        assert result.success is False
        assert result.skipped is True
        assert result.attempts == 3

    def test_all_retries_exhausted_abort(self) -> None:
        rm = RetryManager()
        with pytest.raises(ActionAbortedError):
            rm.execute_with_retry(
                action_fn=lambda: "fail",
                verify_fn=lambda r: False,
                retry_config=RetryConfig(max_count=1),
                on_fail_config=OnFailConfig(policy=OnFailPolicy.ABORT),
            )

    def test_interval_sleep_called(self) -> None:
        rm = RetryManager()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            return "ok" if call_count >= 2 else "fail"
        with patch("td_executor.engine.retry.time.sleep") as mock_sleep:
            result = rm.execute_with_retry(
                action_fn=action,
                verify_fn=lambda r: r == "ok",
                retry_config=RetryConfig(max_count=2, interval_ms=500),
            )
            assert result.success is True
            mock_sleep.assert_called_once_with(0.5)

    def test_no_callback_when_flag_false(self) -> None:
        rm = RetryManager()
        reset_fn = MagicMock()
        adjust_fn = MagicMock()
        call_count = 0
        def action():
            nonlocal call_count
            call_count += 1
            return "ok" if call_count >= 2 else "fail"
        result = rm.execute_with_retry(
            action_fn=action,
            verify_fn=lambda r: r == "ok",
            retry_config=RetryConfig(max_count=2, reset_view_before_retry=False, micro_adjust_on_retry=False),
            reset_view_fn=reset_fn,
            micro_adjust_fn=adjust_fn,
        )
        assert result.success is True
        reset_fn.assert_not_called()
        adjust_fn.assert_not_called()

    def test_default_on_fail_is_skip(self) -> None:
        rm = RetryManager()
        result = rm.execute_with_retry(
            action_fn=lambda: "fail",
            verify_fn=lambda r: False,
            retry_config=RetryConfig(max_count=0),
        )
        assert result.success is False
        assert result.skipped is True
