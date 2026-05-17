"""失败重试策略：支持动作重试、条件等待、失败降级。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class OnConditionFailedPolicy(Enum):
    WAIT = "wait"
    SKIP = "skip"


class OnFailPolicy(Enum):
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class RetryConfig:
    max_count: int = 0
    interval_ms: int = 0
    reset_view_before_retry: bool = False
    micro_adjust_on_retry: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> RetryConfig:
        if not d:
            return cls()
        return cls(
            max_count=d.get("max_count", 0),
            interval_ms=d.get("interval_ms", 0),
            reset_view_before_retry=d.get("reset_view_before_retry", False),
            micro_adjust_on_retry=d.get("micro_adjust_on_retry", False),
        )


@dataclass
class OnConditionFailedConfig:
    policy: OnConditionFailedPolicy = OnConditionFailedPolicy.WAIT
    timeout_ms: int = 30000
    then: str = "retry_condition"

    @classmethod
    def from_dict(cls, d: dict | None) -> OnConditionFailedConfig:
        if not d:
            return cls()
        policy_str = d.get("policy", "wait")
        policy = OnConditionFailedPolicy(policy_str)
        return cls(
            policy=policy,
            timeout_ms=d.get("timeout_ms", 30000),
            then=d.get("then", "retry_condition"),
        )


@dataclass
class OnFailConfig:
    policy: OnFailPolicy = OnFailPolicy.SKIP

    @classmethod
    def from_dict(cls, d: dict | None) -> OnFailConfig:
        if not d:
            return cls()
        policy_str = d.get("policy", "skip")
        policy = OnFailPolicy(policy_str)
        return cls(policy=policy)


@dataclass
class ActionResult:
    success: bool
    skipped: bool = False
    attempts: int = 1
    data: Any = None


class ActionAbortedError(Exception):
    pass


class RetryManager:
    def __init__(self, runtime_defaults: dict | None = None) -> None:
        self._runtime_defaults = runtime_defaults if runtime_defaults is not None else {}

    def resolve_retry_config(self, action_retry: dict | None) -> RetryConfig:
        if action_retry is not None:
            max_count = action_retry.get(
                "max_count",
                self._runtime_defaults.get("default_retry_count", 0),
            )
            interval_ms = action_retry.get("interval_ms", 0)
            reset_view_before_retry = action_retry.get(
                "reset_view_before_retry",
                self._runtime_defaults.get("reset_view_on_retry", False),
            )
            micro_adjust_on_retry = action_retry.get(
                "micro_adjust_on_retry", False
            )
            return RetryConfig(
                max_count=max_count,
                interval_ms=interval_ms,
                reset_view_before_retry=reset_view_before_retry,
                micro_adjust_on_retry=micro_adjust_on_retry,
            )
        return RetryConfig(
            max_count=self._runtime_defaults.get("default_retry_count", 0),
            interval_ms=0,
            reset_view_before_retry=self._runtime_defaults.get(
                "reset_view_on_retry", False
            ),
            micro_adjust_on_retry=False,
        )

    def resolve_on_condition_failed(
        self, action_config: dict | None
    ) -> OnConditionFailedConfig:
        if action_config is not None:
            cfg = OnConditionFailedConfig.from_dict(action_config)
            return cfg
        policy_str = self._runtime_defaults.get("default_resource_policy", "wait")
        timeout_ms = self._runtime_defaults.get(
            "default_wait_resource_timeout_ms", 30000
        )
        return OnConditionFailedConfig(
            policy=OnConditionFailedPolicy(policy_str),
            timeout_ms=timeout_ms,
        )

    def resolve_on_fail(self, action_config: dict | None) -> OnFailConfig:
        return OnFailConfig.from_dict(action_config)

    def wait_for_condition(
        self,
        condition_fn: Callable[[], bool],
        config: OnConditionFailedConfig,
    ) -> bool:
        if config.policy is OnConditionFailedPolicy.SKIP:
            return False
        deadline = time.monotonic() + config.timeout_ms / 1000.0
        while time.monotonic() < deadline:
            if condition_fn():
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.2, remaining))
        if config.then == "retry_condition":
            return condition_fn()
        return False

    def execute_with_retry(
        self,
        action_fn: Callable,
        verify_fn: Callable[[Any], bool],
        retry_config: RetryConfig,
        on_fail_config: OnFailConfig | None = None,
        reset_view_fn: Callable[[], None] | None = None,
        micro_adjust_fn: Callable[[], None] | None = None,
    ) -> ActionResult:
        total_attempts = retry_config.max_count + 1
        last_exception: Exception | None = None
        for attempt in range(total_attempts):
            if attempt > 0:
                if retry_config.reset_view_before_retry and reset_view_fn is not None:
                    reset_view_fn()
                if retry_config.micro_adjust_on_retry and micro_adjust_fn is not None:
                    micro_adjust_fn()
                if retry_config.interval_ms > 0:
                    time.sleep(retry_config.interval_ms / 1000.0)
            try:
                result = action_fn()
            except Exception as exc:
                last_exception = exc
                continue
            if verify_fn(result):
                return ActionResult(
                    success=True, attempts=attempt + 1, data=result
                )
        if on_fail_config is None or on_fail_config.policy is OnFailPolicy.SKIP:
            return ActionResult(
                success=False, skipped=True, attempts=total_attempts
            )
        raise ActionAbortedError
