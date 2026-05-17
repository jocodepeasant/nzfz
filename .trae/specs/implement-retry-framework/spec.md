# 重试框架 (Retry Framework) Spec

## Why
automation-executor 的所有动作执行（放置、升级、拆除、导航）均可能因识别失败、点击偏移、网络延迟等原因失败，需要统一的失败重试与降级策略。当前 `retry.py` 仅为空壳 `RetryManager` 类，导致动作执行无法容错，是执行器从"骨架"走向"可运行"的关键一步。

## What Changes
- 实现 `retry.py` 中的 `RetryManager` 类，支持动作失败重试、条件等待、失败降级全流程
- 新增 `RetryConfig` 数据类，对应脚本 JSON 中的 `retryBlock` 结构
- 新增 `OnConditionFailedConfig` 数据类，对应脚本 JSON 中的 `onConditionFailed` 结构
- 新增 `OnFailConfig` 数据类，对应脚本 JSON 中的 `onFail` 结构
- 新增 `OnConditionFailedPolicy` 枚举（wait / skip）
- 新增 `OnFailPolicy` 枚举（skip / abort）
- 新增 `ActionResult` 数据类，封装动作执行结果（成功/失败/跳过）
- 新增 `ActionAbortedError` 异常类，用于 on_fail.policy=abort 时中断执行
- `RetryManager` 支持从 `runtime` 配置中解析默认值，与动作级配置合并
- `RetryManager` 通过回调机制支持 `reset_view_before_retry` 和 `micro_adjust_on_retry`
- 更新 `engine/__init__.py` 导出新增的公开类型

## Impact
- Affected specs: 动作执行引擎（action.py）的前置依赖，条件引擎（condition.py）的协作方
- Affected code:
  - `automation-executor/src/td_executor/engine/retry.py`（主要修改）
  - `automation-executor/src/td_executor/engine/__init__.py`（导出更新）

## ADDED Requirements

### Requirement: RetryConfig 数据类
系统 SHALL 提供 `RetryConfig` 数据类，封装重试配置参数，对应脚本 JSON 中的 `retryBlock`。

#### Scenario: 默认配置
- **WHEN** 创建 `RetryConfig()` 不传参数
- **THEN** max_count 为 0，interval_ms 为 0，reset_view_before_retry 为 False，micro_adjust_on_retry 为 False

#### Scenario: 从字典构造
- **WHEN** 调用 `RetryConfig.from_dict({"max_count": 3, "interval_ms": 800, "reset_view_before_retry": True, "micro_adjust_on_retry": True})`
- **THEN** 返回 RetryConfig(max_count=3, interval_ms=800, reset_view_before_retry=True, micro_adjust_on_retry=True)

#### Scenario: 从空字典构造
- **WHEN** 调用 `RetryConfig.from_dict({})`
- **THEN** 返回使用默认值的 RetryConfig

#### Scenario: 从 None 构造
- **WHEN** 调用 `RetryConfig.from_dict(None)`
- **THEN** 返回使用默认值的 RetryConfig

### Requirement: OnConditionFailedConfig 数据类
系统 SHALL 提供 `OnConditionFailedConfig` 数据类，封装条件失败处理策略，对应脚本 JSON 中的 `onConditionFailed`。

#### Scenario: 默认配置
- **WHEN** 创建 `OnConditionFailedConfig()` 不传参数
- **THEN** policy 为 OnConditionFailedPolicy.WAIT，timeout_ms 为 30000，then 为 "retry_condition"

#### Scenario: 从字典构造
- **WHEN** 调用 `OnConditionFailedConfig.from_dict({"policy": "skip"})`
- **THEN** 返回 OnConditionFailedConfig(policy=OnConditionFailedPolicy.SKIP, timeout_ms=30000, then="retry_condition")

#### Scenario: 从 None 构造
- **WHEN** 调用 `OnConditionFailedConfig.from_dict(None)`
- **THEN** 返回使用默认值的 OnConditionFailedConfig

### Requirement: OnFailConfig 数据类
系统 SHALL 提供 `OnFailConfig` 数据类，封装动作最终失败处理策略，对应脚本 JSON 中的 `onFail`。

#### Scenario: 默认配置
- **WHEN** 创建 `OnFailConfig()` 不传参数
- **THEN** policy 为 OnFailPolicy.SKIP

#### Scenario: 从字典构造
- **WHEN** 调用 `OnFailConfig.from_dict({"policy": "abort"})`
- **THEN** 返回 OnFailConfig(policy=OnFailPolicy.ABORT)

#### Scenario: 从 None 构造
- **WHEN** 调用 `OnFailConfig.from_dict(None)`
- **THEN** 返回使用默认值的 OnFailConfig

### Requirement: ActionResult 数据类
系统 SHALL 提供 `ActionResult` 数据类，封装动作执行结果。

#### Scenario: 成功结果
- **WHEN** 动作执行并验证通过
- **THEN** ActionResult.success 为 True，skipped 为 False，attempts 为实际尝试次数

#### Scenario: 失败后跳过
- **WHEN** 所有重试用尽且 on_fail.policy 为 skip
- **THEN** ActionResult.success 为 False，skipped 为 True，attempts 为实际尝试次数

#### Scenario: 失败后中止
- **WHEN** 所有重试用尽且 on_fail.policy 为 abort
- **THEN** 抛出 ActionAbortedError 异常

### Requirement: RetryManager 类
系统 SHALL 提供 `RetryManager` 类，管理动作执行的重试、条件等待和失败降级全流程。

#### Scenario: 使用运行时默认值初始化
- **WHEN** 调用 `RetryManager(runtime_defaults={"default_retry_count": 2, "reset_view_on_retry": True, "default_resource_policy": "wait", "default_wait_resource_timeout_ms": 30000})`
- **THEN** RetryManager 持有运行时默认值，用于后续配置合并

#### Scenario: 解析重试配置（动作级覆盖运行时默认）
- **WHEN** 调用 `resolve_retry_config({"max_count": 3, "interval_ms": 800})`
- **THEN** 返回 RetryConfig(max_count=3, interval_ms=800)，其中 reset_view_before_retry 使用运行时默认值 reset_view_on_retry

#### Scenario: 解析重试配置（动作级未指定时使用运行时默认）
- **WHEN** 调用 `resolve_retry_config(None)` 且运行时默认 default_retry_count=2, reset_view_on_retry=True
- **THEN** 返回 RetryConfig(max_count=2, reset_view_before_retry=True)

#### Scenario: 条件等待（policy=wait）
- **WHEN** 调用 `wait_for_condition(condition_fn, on_condition_failed_config)` 且 policy 为 wait
- **THEN** 在 timeout_ms 时间内轮询 condition_fn，若条件满足返回 True；超时后根据 then 字段决定是否做最后一次检查

#### Scenario: 条件等待（policy=skip）
- **WHEN** 调用 `wait_for_condition(condition_fn, on_condition_failed_config)` 且 policy 为 skip
- **THEN** 立即返回 False，不等待

#### Scenario: 带重试的动作执行（首次成功）
- **WHEN** 调用 `execute_with_retry(action_fn, verify_fn, retry_config)` 且 action_fn 首次执行后 verify_fn 返回 True
- **THEN** 返回 ActionResult(success=True, attempts=1)

#### Scenario: 带重试的动作执行（重试后成功）
- **WHEN** 调用 `execute_with_retry(action_fn, verify_fn, retry_config)` 且 action_fn 前两次验证失败，第三次成功
- **THEN** 返回 ActionResult(success=True, attempts=3)，且在重试间隔中调用了 sleep(interval_ms)

#### Scenario: 重试时调用 reset_view 回调
- **WHEN** retry_config.reset_view_before_retry 为 True 且提供了 reset_view_fn
- **THEN** 每次重试前调用 reset_view_fn()

#### Scenario: 重试时调用 micro_adjust 回调
- **WHEN** retry_config.micro_adjust_on_retry 为 True 且提供了 micro_adjust_fn
- **THEN** 每次重试前调用 micro_adjust_fn()

#### Scenario: 所有重试用尽后 skip
- **WHEN** 所有重试用尽且 on_fail_config.policy 为 skip
- **THEN** 返回 ActionResult(success=False, skipped=True)

#### Scenario: 所有重试用尽后 abort
- **WHEN** 所有重试用尽且 on_fail_config.policy 为 abort
- **THEN** 抛出 ActionAbortedError

#### Scenario: action_fn 抛异常时触发重试
- **WHEN** action_fn 抛出异常
- **THEN** 异常被捕获，视为本次尝试失败，继续重试流程

#### Scenario: max_count 为 0 时不重试
- **WHEN** retry_config.max_count 为 0
- **THEN** 仅执行一次，失败后直接应用 on_fail 策略

### Requirement: 与 engine/__init__.py 导出集成
系统 SHALL 在 `engine/__init__.py` 中导出 RetryManager、RetryConfig、OnConditionFailedConfig、OnFailConfig、OnConditionFailedPolicy、OnFailPolicy、ActionResult、ActionAbortedError。

#### Scenario: 导出可用
- **WHEN** 从 `td_executor.engine` 导入上述类型
- **THEN** 所有类型均可正常导入
