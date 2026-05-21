"""重试策略定义：包含重试策略、失败处理策略、条件失败策略等数据类与枚举。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass
class RetryPolicy:
    """重试策略：定义动作执行失败后的重试行为参数。"""

    max_count: int = 3
    """最大重试次数。"""

    interval_ms: int = 500
    """重试间隔时间（毫秒）。"""

    reset_view_before_retry: bool = False
    """重试前是否重置视角。"""

    micro_adjust_on_retry: bool = False
    """重试时是否进行微调。"""

    @classmethod
    def from_dict(cls, d: dict | None) -> RetryPolicy:
        """从字典构建重试策略实例。"""
        raise NotImplementedError


class OnFailPolicy(Enum):
    """失败处理策略：定义动作执行失败后的处理方式。"""

    SKIP = "skip"
    """跳过当前动作，继续执行后续流程。"""

    ABORT = "abort"
    """中止整个执行流程。"""


class OnConditionFailedPolicy(Enum):
    """条件失败策略：定义条件判断失败后的处理方式。"""

    WAIT = "wait"
    """等待条件满足。"""

    SKIP = "skip"
    """跳过当前动作。"""


@dataclass
class OnConditionFailedConfig:
    """条件失败配置：定义条件判断失败后的详细处理参数。"""

    policy: OnConditionFailedPolicy = OnConditionFailedPolicy.WAIT
    """条件失败时采取的策略。"""

    timeout_ms: int = 30000
    """等待超时时间（毫秒）。"""

    then: str = "retry_condition"
    """超时后的后续动作标识。"""

    @classmethod
    def from_dict(cls, d: dict | None) -> OnConditionFailedConfig:
        """从字典构建条件失败配置实例。"""
        raise NotImplementedError