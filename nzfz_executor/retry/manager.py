"""重试管理器：提供动作执行的重试逻辑、策略解析与条件失败处理。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from nzfz_executor.retry.policy import OnConditionFailedConfig, OnFailPolicy, RetryPolicy

if TYPE_CHECKING:
    from nzfz_executor.actions.base import ActionResult


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
        """解析动作级别的重试配置，合并全局默认值。

        Args:
            action_retry: 动作级别的重试配置字典，可为 None。

        Returns:
            合并后的重试策略实例。
        """
        raise NotImplementedError

    def resolve_on_condition_failed(self, action_config: dict | None) -> OnConditionFailedConfig:
        """解析动作的条件失败配置。

        Args:
            action_config: 动作配置字典，可为 None。

        Returns:
            条件失败配置实例。
        """
        raise NotImplementedError

    def execute_with_retry(
        self,
        action_fn: Callable[..., ActionResult],
        verify_fn: Callable[..., bool] | None,
        retry_policy: RetryPolicy,
        on_fail_policy: OnFailPolicy,
    ) -> ActionResult:
        """带重试逻辑执行动作，支持验证与失败策略。

        Args:
            action_fn: 动作执行函数，返回 ActionResult。
            verify_fn: 验证函数，返回是否满足条件，可为 None。
            retry_policy: 重试策略。
            on_fail_policy: 失败处理策略。

        Returns:
            动作执行结果。
        """
        raise NotImplementedError