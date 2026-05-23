"""重试管理器：提供动作执行的重试逻辑、策略解析与条件失败处理。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from nzfz_executor.actions.base import ActionResult
from nzfz_executor.retry.policy import OnConditionFailedConfig, OnFailPolicy, RetryPolicy


class RetryManager:
    """重试管理器：封装动作执行的重试逻辑，支持策略解析与条件失败处理。"""

    def __init__(self, config: dict | None = None) -> None:
        """初始化重试管理器。

        Args:
            config: 全局重试配置字典，可为 None。
        """
        self._config: dict | None = config
        """全局重试配置。"""

    def resolve_retry_config(self, action_retry: dict | None) -> RetryPolicy:
        return RetryPolicy.from_dict(action_retry)

    def resolve_on_condition_failed(self, action_config: dict | None) -> OnConditionFailedConfig:
        config = action_config or {}
        return OnConditionFailedConfig.from_dict(config.get("on_condition_failed"))

    def execute_with_retry(
        self,
        action_fn: Callable[..., ActionResult],
        verify_fn: Callable[..., bool] | None,
        retry_policy: RetryPolicy,
        on_fail_policy: OnFailPolicy,
    ) -> ActionResult:
        del verify_fn, on_fail_policy
        last_result: ActionResult | None = None
        attempts = max(1, retry_policy.max_count + 1)
        for attempt in range(1, attempts + 1):
            last_result = action_fn()
            if last_result.success:
                return ActionResult(
                    success=True,
                    attempts=attempt,
                    data=last_result.data,
                )
            if attempt < attempts and retry_policy.interval_ms > 0:
                import time

                time.sleep(retry_policy.interval_ms / 1000.0)
        return ActionResult(
            success=False,
            attempts=attempts,
            error=last_result.error if last_result else "动作执行失败",
        )