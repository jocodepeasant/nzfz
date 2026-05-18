# Tasks

- [ ] Task 1: 实现 ActionExecutor 类框架
  - [ ] SubTask 1.1: 定义 ActionExecutor.__init__，初始化 RetryManager、ConditionEngine、VisionDetector
  - [ ] SubTask 1.2: 实现 ActionExecutor.execute 调度方法，根据 action["type"] 分发
  - [ ] SubTask 1.3: 保留模块级 execute_action 便捷函数，内部创建默认 ActionExecutor

- [ ] Task 2: 实现 _execute_place_trap 放置陷阱流程
  - [ ] SubTask 2.1: ensure_map_open → locate_slot → pan_to_region 前置流程
  - [ ] SubTask 2.2: 条件判断 + on_condition_failed 处理（wait/skip）
  - [ ] SubTask 2.3: 查找 trap 获取 select_key → press_key → click_slot
  - [ ] SubTask 2.4: 构建 verify_fn（slot_has_trap → detector.is_slot_occupied）
  - [ ] SubTask 2.5: RetryManager.execute_with_retry 集成，传入 reset_view_fn 和 micro_adjust_fn
  - [ ] SubTask 2.6: 放置成功后更新 state.trap_levels[trap_id] = 1

- [ ] Task 3: 实现 _execute_upgrade_trap 升级陷阱流程
  - [ ] SubTask 3.1: ensure_map_open 前置流程
  - [ ] SubTask 3.2: 条件判断 + on_condition_failed 处理
  - [ ] SubTask 3.3: 解析 execute 参数（优先 action.execute，回退 trap 配置）
  - [ ] SubTask 3.4: press_key(key, hold_ms) 长按升级键
  - [ ] SubTask 3.5: 构建 verify_fn（trap_level_gte → 检查 state 或 required=false 跳过）
  - [ ] SubTask 3.6: RetryManager.execute_with_retry 集成
  - [ ] SubTask 3.7: 升级成功后更新 state.trap_levels[trap_id] = target_level

- [ ] Task 4: 实现 _execute_remove_trap 拆除陷阱流程
  - [ ] SubTask 4.1: ensure_map_open → locate_slot → pan_to_region 前置流程
  - [ ] SubTask 4.2: 条件判断 + on_condition_failed 处理
  - [ ] SubTask 4.3: 解析 execute.method，custom_steps 为空时默认点击格子
  - [ ] SubTask 4.4: 构建 verify_fn（slot_empty → detector.is_slot_empty）
  - [ ] SubTask 4.5: RetryManager.execute_with_retry 集成
  - [ ] SubTask 4.6: 拆除成功后移除 state.trap_levels 中对应条目

- [ ] Task 5: 实现 _execute_pan_to_region 地图导航流程
  - [ ] SubTask 5.1: 调用 navigator.pan_to_region
  - [ ] SubTask 5.2: 失败时根据 retry 配置重试

- [ ] Task 6: 实现 verify 校验函数构建逻辑
  - [ ] SubTask 6.1: _build_verify_fn 方法，根据 verify.type 构建校验函数
  - [ ] SubTask 6.2: slot_has_trap → detector.is_slot_occupied
  - [ ] SubTask 6.3: slot_empty → detector.is_slot_empty
  - [ ] SubTask 6.4: trap_level_gte → 检查 state 或 required=false 跳过
  - [ ] SubTask 6.5: 未知类型 → warning + required 判断

- [ ] Task 7: 更新 engine/__init__.py 导出
  - [ ] SubTask 7.1: 添加 ActionExecutor 类的导入和导出

- [ ] Task 8: 编写测试 test_action_executor.py
  - [ ] SubTask 8.1: 测试 ActionExecutor 初始化
  - [ ] SubTask 8.2: 测试 execute 调度（log/未知类型）
  - [ ] SubTask 8.3: 测试 place_trap 完整流程（成功/条件跳过/条件等待超时/重试成功/地图未打开）
  - [ ] SubTask 8.4: 测试 upgrade_trap 完整流程（成功/使用 execute 参数/回退 trap 配置/状态更新）
  - [ ] SubTask 8.5: 测试 remove_trap 完整流程（默认点击/自定义步骤/状态更新）
  - [ ] SubTask 8.6: 测试 pan_to_region 流程（成功/失败）
  - [ ] SubTask 8.7: 测试 verify 函数构建（各类型）
  - [ ] SubTask 8.8: 测试模块级 execute_action 便捷函数

# Task Dependencies

- Task 2~5 依赖 Task 1（需要 ActionExecutor 类框架）
- Task 6 依赖 Task 1（需要 ActionExecutor 类）
- Task 7 依赖 Task 1~6（需要所有实现完成）
- Task 8 依赖 Task 1~7（需要所有实现完成）
- Task 2 和 Task 3 和 Task 4 和 Task 5 可并行开发
