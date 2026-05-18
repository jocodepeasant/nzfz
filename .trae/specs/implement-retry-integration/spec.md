# T11 重试集成 Spec

## Why

`RetryManager`（T03）已实现底层重试/条件等待/失败降级机制，但尚未与实际动作执行流程串联。T11 需要创建高层编排函数，将 `ConditionEngine`（条件判断）、`RetryManager`（重试管理）、`go_to_origin`（视野重置）、`click_slot(micro_adjust=True)`（微调点击）整合为完整的"条件检查 → 等待/跳过 → 动作执行 → 验证 → 重试 → 失败降级"流程。这是 T10（动作执行完整流程）的核心执行引擎。

## What Changes

- 在 `automation-executor/src/td_executor/engine/retry.py` 中新增 `execute_with_conditions` 高层编排函数
- 新增 `ActionContext` 数据类，封装动作执行所需的运行时上下文（用于传递给 reset_view_fn 和 micro_adjust_fn）
- 实现 `reset_view_before_retry` 与 `go_to_origin` 的集成
- 实现 `micro_adjust_on_retry` 与 `click_slot(micro_adjust=True)` 的集成
- 更新 `engine/__init__.py` 导出新类型

## Impact

- Affected specs: T10（动作执行完整流程）将调用 `execute_with_conditions`
- Affected code:
  - `automation-executor/src/td_executor/engine/retry.py` — 主要修改文件
  - `automation-executor/src/td_executor/engine/__init__.py` — 新增导出
- 依赖模块（只读使用）:
  - `td_executor.engine.condition` → `ConditionEngine`, `ConditionContext`
  - `td_executor.engine.navigator` → `go_to_origin`
  - `td_executor.engine.slot` → `click_slot`
  - `td_executor.runtime.capture` → `ScreenCapture`
  - `td_executor.runtime.window` → `WindowRect`

## ADDED Requirements

### Requirement: execute_with_conditions 高层编排函数

系统 SHALL 提供 `execute_with_conditions` 函数，将条件检查、条件等待、动作执行、验证、重试、失败降级整合为完整流程。

#### Scenario: 条件满足，动作首次执行成功

- **WHEN** `execute_with_conditions` 被调用，且条件检查通过，动作首次执行成功且验证通过
- **THEN** 返回 `ActionResult(success=True, attempts=1)`

#### Scenario: 条件不满足，策略为 skip

- **WHEN** `execute_with_conditions` 被调用，且条件检查不满足，`on_condition_failed.policy` 为 `skip`
- **THEN** 返回 `ActionResult(success=False, skipped=True, attempts=0)`

#### Scenario: 条件不满足，策略为 wait，等待后条件满足

- **WHEN** `execute_with_conditions` 被调用，且条件检查不满足，`on_condition_failed.policy` 为 `wait`
- **THEN** 调用 `RetryManager.wait_for_condition` 等待条件满足，条件满足后继续执行动作

#### Scenario: 条件不满足，策略为 wait，等待超时

- **WHEN** `execute_with_conditions` 被调用，且条件检查不满足，`on_condition_failed.policy` 为 `wait`，等待超时后条件仍不满足
- **THEN** 返回 `ActionResult(success=False, skipped=True, attempts=0)`

#### Scenario: 动作执行失败，重试后成功

- **WHEN** `execute_with_conditions` 被调用，且动作首次执行失败，重试后成功
- **THEN** 返回 `ActionResult(success=True, attempts=N)`，其中 N 为总尝试次数

#### Scenario: 动作执行失败，重试耗尽，on_fail 策略为 skip

- **WHEN** `execute_with_conditions` 被调用，且动作重试耗尽仍失败，`on_fail.policy` 为 `skip`
- **THEN** 返回 `ActionResult(success=False, skipped=True, attempts=N)`

#### Scenario: 动作执行失败，重试耗尽，on_fail 策略为 abort

- **WHEN** `execute_with_conditions` 被调用，且动作重试耗尽仍失败，`on_fail.policy` 为 `abort`
- **THEN** 抛出 `ActionAbortedError`

### Requirement: ActionContext 动作执行上下文

系统 SHALL 提供 `ActionContext` 数据类，封装动作执行所需的运行时上下文信息，用于构建 `reset_view_fn` 和 `micro_adjust_fn` 回调。

#### Scenario: ActionContext 包含执行所需数据

- **WHEN** 创建 `ActionContext` 实例
- **THEN** 包含 `capture`（ScreenCapture）、`rect`（WindowRect）、`rois`（dict）、`slots`（list[dict]）、`regions`（list[dict]）、`runtime`（dict）、`slot_id`（str | None）字段

### Requirement: reset_view_before_retry 集成

系统 SHALL 在 `retry_config.reset_view_before_retry=True` 时，将 `go_to_origin` 作为 `reset_view_fn` 传入 `RetryManager.execute_with_retry`。

#### Scenario: 重试前重置视野

- **WHEN** `execute_with_conditions` 被调用，且 `retry_config.reset_view_before_retry=True`
- **THEN** 每次重试前调用 `go_to_origin(capture, rect, rois, runtime)` 重置视野

#### Scenario: 不重置视野

- **WHEN** `execute_with_conditions` 被调用，且 `retry_config.reset_view_before_retry=False`
- **THEN** 重试前不调用 `go_to_origin`

### Requirement: micro_adjust_on_retry 集成

系统 SHALL 在 `retry_config.micro_adjust_on_retry=True` 时，将 `click_slot(slot_id, rect, slots, micro_adjust=True)` 作为 `micro_adjust_fn` 传入 `RetryManager.execute_with_retry`。

#### Scenario: 重试时微调点击

- **WHEN** `execute_with_conditions` 被调用，且 `retry_config.micro_adjust_on_retry=True`，且 `action_ctx.slot_id` 不为 None
- **THEN** 每次重试前调用 `click_slot(slot_id, rect, slots, micro_adjust=True)` 微调点击位置

#### Scenario: 无 slot_id 时不微调

- **WHEN** `execute_with_conditions` 被调用，且 `retry_config.micro_adjust_on_retry=True`，但 `action_ctx.slot_id` 为 None
- **THEN** 不执行微调点击

### Requirement: 条件检查与 ConditionEngine 集成

系统 SHALL 在动作执行前使用 `ConditionEngine.eval_conditions` 检查动作的 `conditions` 配置。

#### Scenario: 无条件配置

- **WHEN** `execute_with_conditions` 被调用，且动作的 `conditions` 为空或 None
- **THEN** 跳过条件检查，直接执行动作

#### Scenario: 条件检查使用 ConditionEngine

- **WHEN** `execute_with_conditions` 被调用，且动作的 `conditions` 不为空
- **THEN** 使用 `ConditionEngine.eval_conditions(conditions, condition_ctx)` 检查条件

### Requirement: RetryManager 配置解析集成

系统 SHALL 使用 `RetryManager` 的 `resolve_*` 方法从动作配置和运行时默认值中解析重试/条件/失败策略。

#### Scenario: 从动作配置解析重试参数

- **WHEN** `execute_with_conditions` 被调用
- **THEN** 使用 `RetryManager.resolve_retry_config(action.get("retry"))` 解析重试配置

#### Scenario: 从动作配置解析条件失败策略

- **WHEN** `execute_with_conditions` 被调用
- **THEN** 使用 `RetryManager.resolve_on_condition_failed(action.get("on_condition_failed"))` 解析条件失败策略

#### Scenario: 从动作配置解析失败策略

- **WHEN** `execute_with_conditions` 被调用
- **THEN** 使用 `RetryManager.resolve_on_fail(action.get("on_fail"))` 解析失败策略

## MODIFIED Requirements

### Requirement: engine/__init__.py 导出更新

`engine/__init__.py` SHALL 新增导出 `execute_with_conditions` 和 `ActionContext`。
