# T10 - 动作执行完整流程 Spec

## Why

自动化执行器需要将脚本 JSON 中的 waveAction 调度为完整的执行流程，包括条件判断、导航、按键操作、校验和重试。T07 仅实现了底层原语和 log 类型，T10 需要补全 place_trap、upgrade_trap、remove_trap、pan_to_region 四种动作的完整执行逻辑，这是整个自动化系统的核心串联层。

## What Changes

- 在 `automation-executor/src/td_executor/engine/action.py` 中引入 `ActionExecutor` 类，持有 `RetryManager`、`ConditionEngine`、`VisionDetector` 实例
- 实现 `_execute_place_trap`：确保地图打开 → 导航到 region → 条件判断 → 按选择键 → 点击格子 → 校验 → 重试
- 实现 `_execute_upgrade_trap`：确保地图打开 → 条件判断 → 长按升级键 → 校验 → 重试
- 实现 `_execute_remove_trap`：确保地图打开 → 导航到 region → 条件判断 → 点击格子 → 校验 → 重试
- 实现 `_execute_pan_to_region`：调用 navigator.pan_to_region → 重试
- 重构 `execute_action` 为 `ActionExecutor.execute` 方法，保留模块级 `execute_action` 函数作为便捷入口
- 升级成功后更新 `context["state"]["trap_levels"]`
- 更新 `engine/__init__.py` 导出新增类型

## Impact

- Affected specs: T11（重试集成）、T12（日志集成）、T13（批量执行）
- Affected code: `automation-executor/src/td_executor/engine/action.py`（主要修改）、`automation-executor/src/td_executor/engine/__init__.py`（导出更新）
- 新增测试: `automation-executor/tests/test_action_executor.py`

## ADDED Requirements

### Requirement: ActionExecutor 类

系统 SHALL 提供 `ActionExecutor` 类，作为动作执行的统一入口，持有运行时依赖实例。

- 构造函数 `__init__(self, runtime_defaults: dict | None = None, detector: VisionDetector | None = None)` 初始化 `RetryManager`、`ConditionEngine`、`VisionDetector`
- `detector` 参数为 None 时，创建默认 `VisionDetector()` 实例
- `runtime_defaults` 传入 `RetryManager` 用于解析默认重试/条件失败/失败策略配置
- `execute(self, action: dict, context: dict) -> dict` 方法作为动作调度入口

#### Scenario: 创建 ActionExecutor 实例
- **WHEN** 调用 `ActionExecutor(runtime_defaults=script["runtime"])`
- **THEN** 内部创建 RetryManager、ConditionEngine 和默认 VisionDetector 实例

### Requirement: 动作调度 execute

`ActionExecutor.execute` SHALL 根据 `action["type"]` 分发到对应的处理方法。

- `type="log"` → 打印消息，返回 `{"success": True, "skipped": False}`
- `type="place_trap"` → 调用 `_execute_place_trap`
- `type="upgrade_trap"` → 调用 `_execute_upgrade_trap`
- `type="remove_trap"` → 调用 `_execute_remove_trap`
- `type="pan_to_region"` → 调用 `_execute_pan_to_region`
- 未知类型 → 打印 warning，返回 `{"success": False, "skipped": False, "error": "unknown action type: <type>"}`

### Requirement: place_trap 执行流程

`_execute_place_trap` SHALL 按以下流程执行放置陷阱动作：

1. 从 context 获取 `capture`, `rect`, `rois`, `slots`, `traps`, `regions`, `runtime`, `state`, `multi_frame`, `wave`
2. 调用 `ensure_map_open(capture, rect, rois)`，失败则返回 `{"success": False, "skipped": False, "error": "map not open"}`
3. 调用 `locate_slot(slot_id, rect, slots)` 获取定位信息，失败则返回错误
4. 调用 `pan_to_region(info["region_id"], rect, regions, capture, rois, runtime)`，失败则返回错误
5. 创建 `ConditionContext` 并调用 `ConditionEngine.eval_conditions` 检查条件
6. 条件不满足时，调用 `RetryManager.resolve_on_condition_failed` 获取策略：
   - `WAIT` → 调用 `RetryManager.wait_for_condition` 等待条件满足，超时后根据 `then` 决定重试或跳过
   - `SKIP` → 返回 `{"success": False, "skipped": True}`
7. 从 `traps` 列表查找 `trap_id` 对应的陷阱配置，获取 `select_key`
8. 调用 `press_key(trap["select_key"])` 选择陷阱
9. 调用 `click_slot(slot_id, rect, slots)` 点击格子
10. 等待 `runtime.get("wait_after_place_ms", 600)` 毫秒
11. 调用 `RetryManager.execute_with_retry` 包装上述操作，传入：
    - `action_fn`：步骤 8-9 的闭包
    - `verify_fn`：根据 `action["verify"]` 构建的校验函数
    - `retry_config`：`RetryManager.resolve_retry_config(action.get("retry"))`
    - `on_fail_config`：`RetryManager.resolve_on_fail(action.get("on_fail"))`
    - `reset_view_fn`：若 `retry_config.reset_view_before_retry`，则闭包调用 `go_to_origin(capture, rect, rois, runtime)` + `pan_to_region`
    - `micro_adjust_fn`：若 `retry_config.micro_adjust_on_retry`，则闭包调用 `click_slot(slot_id, rect, slots, micro_adjust=True)`
12. 返回 `ActionResult` 转换为 dict

#### Scenario: 成功放置陷阱
- **WHEN** 条件满足、导航成功、选择键点击成功、格子点击成功、校验通过
- **THEN** 返回 `{"success": True, "skipped": False, "attempts": 1}`

#### Scenario: 条件不满足且策略为 skip
- **WHEN** 资源不足且 `on_condition_failed.policy = "skip"`
- **THEN** 返回 `{"success": False, "skipped": True}`

#### Scenario: 条件不满足且策略为 wait，超时后跳过
- **WHEN** 资源不足且 `on_condition_failed.policy = "wait"`，等待超时
- **THEN** 返回 `{"success": False, "skipped": True}`

#### Scenario: 放置失败后重试成功
- **WHEN** 第一次放置校验失败，重试后成功
- **THEN** 返回 `{"success": True, "skipped": False, "attempts": 2}`

### Requirement: upgrade_trap 执行流程

`_execute_upgrade_trap` SHALL 按以下流程执行升级陷阱动作：

1. 从 context 获取运行时参数
2. 调用 `ensure_map_open(capture, rect, rois)`
3. 创建 `ConditionContext` 并检查条件
4. 条件不满足时按 `on_condition_failed` 策略处理
5. 从 `traps` 列表查找 `trap_id` 对应的陷阱配置
6. 优先使用 `action["execute"]` 中的 `key` 和 `hold_ms`，回退到 `trap["upgrade_key"]` 和 `trap["upgrade_hold_ms"]`
7. 调用 `press_key(key, hold_ms=hold_ms)` 长按升级键
8. 等待 `runtime.get("wait_after_upgrade_ms", 1000)` 毫秒
9. 调用 `RetryManager.execute_with_retry` 包装上述操作
10. 升级成功后更新 `context["state"]["trap_levels"][trap_id] = target_level`
11. 返回结果

#### Scenario: 成功升级陷阱
- **WHEN** 条件满足、长按升级键成功、校验通过
- **THEN** 返回成功结果，`context["state"]["trap_levels"][trap_id]` 更新为 `target_level`

#### Scenario: 使用 action.execute 中的参数
- **WHEN** `action["execute"] = {"method": "hold_key", "key": "2", "hold_ms": 4000}`
- **THEN** 使用 `key="2"`, `hold_ms=4000` 执行长按

#### Scenario: 回退到 trap 配置的升级参数
- **WHEN** `action["execute"]` 缺失或 method 不是 "hold_key"
- **THEN** 使用 `trap["upgrade_key"]` 和 `trap["upgrade_hold_ms"]`

### Requirement: remove_trap 执行流程

`_execute_remove_trap` SHALL 按以下流程执行拆除陷阱动作：

1. 从 context 获取运行时参数
2. 调用 `ensure_map_open(capture, rect, rois)`
3. 调用 `locate_slot(slot_id, rect, slots)` 获取定位信息
4. 调用 `pan_to_region(info["region_id"], rect, regions, capture, rois, runtime)`
5. 创建 `ConditionContext` 并检查条件
6. 条件不满足时按 `on_condition_failed` 策略处理
7. 检查 `action["execute"]["method"]`：
   - `"custom_steps"` 且 `steps` 非空 → 执行自定义步骤（T10 阶段预留，打印 warning 并跳过）
   - 其他情况（包括 `custom_steps` 的 `steps` 为空）→ 默认方式：调用 `click_slot(slot_id, rect, slots)` 点击格子
8. 等待 `runtime.get("wait_after_remove_ms", 600)` 毫秒
9. 调用 `RetryManager.execute_with_retry` 包装上述操作
10. 返回结果

#### Scenario: 默认方式拆除
- **WHEN** `execute.custom_steps.steps` 为空
- **THEN** 调用 `click_slot(slot_id, rect, slots)` 点击格子位置

#### Scenario: 自定义步骤拆除
- **WHEN** `execute.custom_steps.steps` 非空
- **THEN** 打印 warning 日志，跳过执行，返回 `{"success": False, "skipped": True, "error": "custom_steps not implemented"}`

### Requirement: pan_to_region 执行流程

`_execute_pan_to_region` SHALL 按以下流程执行地图导航动作：

1. 从 context 获取 `capture`, `rect`, `rois`, `regions`, `runtime`
2. 调用 `pan_to_region(region_id, rect, regions, capture, rois, runtime)`
3. 失败时根据 `retry` 配置重试
4. 返回结果

#### Scenario: 成功导航
- **WHEN** `pan_to_region` 返回 True
- **THEN** 返回 `{"success": True, "skipped": False, "attempts": 1}`

#### Scenario: 导航失败
- **WHEN** `pan_to_region` 返回 False
- **THEN** 返回 `{"success": False, "skipped": False, "error": "pan_to_region failed"}`

### Requirement: verify 校验函数构建

系统 SHALL 根据 `action["verify"]` 的 `type` 字段动态构建校验函数。

- `verify.type == "slot_has_trap"` → 调用 `detector.is_slot_occupied(capture, rect, slot_verify)`
- `verify.type == "slot_empty"` → 调用 `detector.is_slot_empty(capture, rect, slot_verify)`
- `verify.type == "trap_level_gte"` → 检查 `context["state"]["trap_levels"][trap_id] >= level`，若 state 中无数据则返回 `not verify.get("required", True)`
- `verify` 为空或 `required == False` 且无法校验 → 返回 True（校验通过）
- 未知 verify.type → 打印 warning，返回 `not verify.get("required", True)`

#### Scenario: slot_has_trap 校验
- **WHEN** `verify = {"type": "slot_has_trap", "slot_id": "A01", "required": true}`
- **THEN** 调用 `detector.is_slot_occupied(capture, rect, slot.verify)` 返回校验结果

#### Scenario: trap_level_gte 校验且 required=false
- **WHEN** `verify = {"type": "trap_level_gte", "trap_id": "damage_trap", "level": 2, "required": false}` 且 state 中无该 trap 数据
- **THEN** 返回 True（校验通过，因为 required=false）

### Requirement: state 陷阱等级维护

系统 SHALL 在升级陷阱成功后更新 `context["state"]["trap_levels"]` 字典。

- 升级成功后设置 `context.setdefault("state", {}).setdefault("trap_levels", {})[trap_id] = target_level`
- `context["state"]` 或 `context["state"]["trap_levels"]` 不存在时自动创建
- 放置陷阱成功后可设置 `trap_levels[trap_id] = 1`（初始等级）
- 拆除陷阱成功后可移除 `trap_levels` 中对应条目

### Requirement: 模块级便捷函数

系统 SHALL 保留模块级 `execute_action(action: dict, context: dict) -> dict` 函数作为便捷入口。

- 内部创建默认 `ActionExecutor` 实例并调用 `execute`
- 每次调用创建新实例，不持有状态
- 保留向后兼容性，T07 的 log 类型行为不变

## MODIFIED Requirements

### Requirement: engine 包导出

`td_executor.engine.__init__` SHALL 导出 `ActionExecutor` 类，供外部模块直接 `from td_executor.engine import ActionExecutor` 使用。
