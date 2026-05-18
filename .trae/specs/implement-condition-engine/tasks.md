# Tasks

- [x] Task 1: 实现 ConditionContext 数据类和 ConditionEngine 类骨架
  - [x] SubTask 1.1: 定义 `ConditionContext` 数据类，包含 capture、rect、rois、slots、traps、state、multi_frame 字段
  - [x] SubTask 1.2: 定义 `ConditionEngine` 类，`__init__` 接收 `VisionDetector` 实例（可选），内部维护 OCR 缓存字典
  - [x] SubTask 1.3: 实现 `eval_conditions` 方法框架：遍历 conditions 字典，短路求值，空条件返回 True，未知键打印 warning 跳过

- [x] Task 2: 实现 6 种条件评估逻辑
  - [x] SubTask 2.1: 实现 `resource_gte` 条件：调用 `read_resource`（带缓存），判断 `resource >= value`
  - [x] SubTask 2.2: 实现 `wave_eq` 条件：调用 `read_wave`（带缓存），判断 `wave == value`
  - [x] SubTask 2.3: 实现 `wave_gte` 条件：复用 `read_wave` 缓存，判断 `wave >= value`
  - [x] SubTask 2.4: 实现 `slot_empty` 条件：根据 slot_id 查找 slot 的 verify 配置，调用 `VisionDetector.is_slot_empty`
  - [x] SubTask 2.5: 实现 `slot_occupied` 条件：根据 slot_id 查找 slot 的 verify 配置，调用 `VisionDetector.is_slot_occupied`
  - [x] SubTask 2.6: 实现 `trap_level_lt` 条件：从 state 字典查找陷阱等级，判断 `current_level < level`，无数据返回 True

- [x] Task 3: 实现模块级 eval_conditions 便捷函数并更新导出
  - [x] SubTask 3.1: 实现模块级 `eval_conditions` 函数，内部创建 ConditionEngine 并委托执行
  - [x] SubTask 3.2: 更新 `engine/__init__.py`，新增导出 `ConditionEngine` 和 `ConditionContext`

- [x] Task 4: 编写单元测试
  - [x] SubTask 4.1: 测试 ConditionContext 数据类实例化
  - [x] SubTask 4.2: 测试空条件/None 条件返回 True
  - [x] SubTask 4.3: 测试 resource_gte 条件（满足/不满足/OCR 返回 None）
  - [x] SubTask 4.4: 测试 wave_eq 和 wave_gte 条件（满足/不满足/OCR 返回 None）
  - [x] SubTask 4.5: 测试 slot_empty 和 slot_occupied 条件
  - [x] SubTask 4.6: 测试 trap_level_lt 条件（满足/不满足/state 无数据）
  - [x] SubTask 4.7: 测试未知条件键不崩溃
  - [x] SubTask 4.8: 测试 OCR 结果缓存复用（read_wave/read_resource 只调用一次）
  - [x] SubTask 4.9: 测试短路求值（条件不满足时后续条件不再评估）
  - [x] SubTask 4.10: 测试模块级 eval_conditions 便捷函数

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 1, Task 2, Task 3]
