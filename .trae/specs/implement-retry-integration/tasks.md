# Tasks

- [ ] Task 1: 实现 ActionContext 数据类和 reset_view/micro_adjust 回调构建
  - [ ] SubTask 1.1: 定义 `ActionContext` 数据类，包含 capture、rect、rois、slots、regions、runtime、slot_id 字段
  - [ ] SubTask 1.2: 实现 `_build_reset_view_fn`：根据 ActionContext 创建调用 `go_to_origin` 的回调函数
  - [ ] SubTask 1.3: 实现 `_build_micro_adjust_fn`：根据 ActionContext 创建调用 `click_slot(micro_adjust=True)` 的回调函数

- [ ] Task 2: 实现 execute_with_conditions 高层编排函数
  - [ ] SubTask 2.1: 实现条件检查流程：使用 ConditionEngine.eval_conditions 检查条件，无条件则跳过
  - [ ] SubTask 2.2: 实现条件等待流程：条件不满足时，根据 on_condition_failed 策略调用 RetryManager.wait_for_condition 或直接 skip
  - [ ] SubTask 2.3: 实现动作执行+重试流程：使用 RetryManager.execute_with_retry 执行动作，传入 reset_view_fn 和 micro_adjust_fn
  - [ ] SubTask 2.4: 实现配置解析：使用 RetryManager.resolve_retry_config、resolve_on_condition_failed、resolve_on_fail 从动作配置和运行时默认值解析参数

- [ ] Task 3: 更新导出
  - [ ] SubTask 3.1: 更新 `engine/__init__.py`，新增导出 `execute_with_conditions` 和 `ActionContext`

- [ ] Task 4: 编写单元测试
  - [ ] SubTask 4.1: 测试 ActionContext 数据类实例化
  - [ ] SubTask 4.2: 测试 _build_reset_view_fn 回调正确调用 go_to_origin
  - [ ] SubTask 4.3: 测试 _build_micro_adjust_fn 回调正确调用 click_slot
  - [ ] SubTask 4.4: 测试 _build_micro_adjust_fn slot_id 为 None 时不调用
  - [ ] SubTask 4.5: 测试条件满足时直接执行动作
  - [ ] SubTask 4.6: 测试条件不满足 + skip 策略返回 skipped
  - [ ] SubTask 4.7: 测试条件不满足 + wait 策略等待后满足
  - [ ] SubTask 4.8: 测试条件不满足 + wait 策略超时
  - [ ] SubTask 4.9: 测试动作执行失败 + 重试成功
  - [ ] SubTask 4.10: 测试动作执行失败 + 重试耗尽 + on_fail=skip
  - [ ] SubTask 4.11: 测试动作执行失败 + 重试耗尽 + on_fail=abort 抛出 ActionAbortedError
  - [ ] SubTask 4.12: 测试 reset_view_before_retry=True 时重试前调用 go_to_origin
  - [ ] SubTask 4.13: 测试 micro_adjust_on_retry=True 时重试前调用 click_slot
  - [ ] SubTask 4.14: 测试无条件配置时跳过条件检查
  - [ ] SubTask 4.15: 测试 RetryManager 配置解析正确合并动作配置和运行时默认值

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 1, Task 2, Task 3]
