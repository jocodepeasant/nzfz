# T06 条件引擎 Spec

## Why

动作执行前需要判断前置条件（资源是否足够、波次是否匹配、格子是否空闲等），条件引擎负责解析脚本 JSON 中的 `conditions` 对象，调用 OCR 和检测器获取实时游戏数据，评估条件是否满足。这是动作执行流程（T10）的核心前置模块。

## What Changes

- 替换 `automation-executor/src/td_executor/engine/condition.py` 的占位实现，完成完整的条件评估引擎
- 新增 `ConditionEngine` 类，封装条件评估逻辑与 OCR/检测器依赖
- 新增 `ConditionContext` 数据类，在同一轮评估中缓存 OCR 结果，避免重复截图和识别
- 支持 6 种条件类型：`resource_gte`、`wave_eq`、`wave_gte`、`slot_empty`、`slot_occupied`、`trap_level_lt`
- 更新 `engine/__init__.py` 导出新类型

## Impact

- Affected specs: T10（动作执行完整流程）将调用条件引擎
- Affected code:
  - `automation-executor/src/td_executor/engine/condition.py` — 主要修改文件
  - `automation-executor/src/td_executor/engine/__init__.py` — 新增导出
- 依赖模块（只读使用）:
  - `td_executor.vision.ocr` → `read_wave`, `read_resource`
  - `td_executor.vision.detector` → `VisionDetector.is_slot_empty`, `VisionDetector.is_slot_occupied`
  - `td_executor.runtime.capture` → `ScreenCapture`
  - `td_executor.runtime.window` → `WindowRect`

## ADDED Requirements

### Requirement: ConditionEngine 条件评估引擎

系统 SHALL 提供 `ConditionEngine` 类，接收 OCR 引擎和检测器实例，对脚本 JSON 中的 `conditions` 对象进行评估。

#### Scenario: 所有条件满足

- **WHEN** `eval_conditions` 被调用，且 `conditions` 中所有条件键对应的实时数据均满足条件值
- **THEN** 返回 `True`

#### Scenario: 任一条件不满足（短路求值）

- **WHEN** `eval_conditions` 被调用，且 `conditions` 中存在不满足的条件
- **THEN** 立即返回 `False`，不再评估后续条件

#### Scenario: 条件为空

- **WHEN** `eval_conditions` 被调用，且 `conditions` 为空 dict 或 None
- **THEN** 返回 `True`（无条件限制视为始终满足）

#### Scenario: 未知条件键

- **WHEN** `eval_conditions` 被调用，且 `conditions` 中包含未知的条件键
- **THEN** 打印 warning 日志，跳过该条件键，不崩溃

### Requirement: 条件类型映射

系统 SHALL 支持以下 6 种条件类型：

| 条件键 | 值类型 | 含义 | 数据来源 |
|--------|--------|------|---------|
| `resource_gte` | `int` | 资源 >= N | OCR `read_resource` |
| `wave_eq` | `int` | 波次 == N | OCR `read_wave` |
| `wave_gte` | `int` | 波次 >= N | OCR `read_wave` |
| `slot_empty` | `str` (slot_id) | 格子为空 | 检测器 `is_slot_empty` |
| `slot_occupied` | `str` (slot_id) | 格子已占用 | 检测器 `is_slot_occupied` |
| `trap_level_lt` | `dict` (`{trap_id, level}`) | 陷阱等级 < N | 状态缓存 |

#### Scenario: resource_gte 条件

- **WHEN** `conditions` 包含 `"resource_gte": 500`
- **THEN** 调用 `read_resource` 获取当前资源值，判断 `resource >= 500`

#### Scenario: wave_eq 条件

- **WHEN** `conditions` 包含 `"wave_eq": 2`
- **THEN** 调用 `read_wave` 获取当前波次，判断 `wave == 2`

#### Scenario: wave_gte 条件

- **WHEN** `conditions` 包含 `"wave_gte": 3`
- **THEN** 调用 `read_wave` 获取当前波次，判断 `wave >= 3`

#### Scenario: slot_empty 条件

- **WHEN** `conditions` 包含 `"slot_empty": "A01"`
- **THEN** 根据 slot_id 在 slots 列表中找到对应 slot 的 `verify` 配置，调用 `VisionDetector.is_slot_empty` 判断

#### Scenario: slot_occupied 条件

- **WHEN** `conditions` 包含 `"slot_occupied": "A01"`
- **THEN** 根据 slot_id 在 slots 列表中找到对应 slot 的 `verify` 配置，调用 `VisionDetector.is_slot_occupied` 判断

#### Scenario: trap_level_lt 条件

- **WHEN** `conditions` 包含 `"trap_level_lt": {"trap_id": "damage_trap", "level": 2}`
- **THEN** 从 `state` 字典中查找 `trap_levels[trap_id]`，判断 `current_level < level`；若 state 中无数据则返回 `True`（保守策略，不阻塞动作执行）

### Requirement: OCR 结果缓存

系统 SHALL 在同一轮 `eval_conditions` 调用中缓存 OCR 识别结果（`read_wave` 和 `read_resource`），避免对同一数据重复截图和识别。

#### Scenario: 同一轮评估中多次引用同一 OCR 数据

- **WHEN** `conditions` 同时包含 `wave_eq` 和 `wave_gte`
- **THEN** `read_wave` 只调用一次，结果缓存后复用

### Requirement: ConditionContext 评估上下文

系统 SHALL 提供 `ConditionContext` 数据类，封装条件评估所需的运行时上下文信息。

#### Scenario: ConditionContext 包含评估所需数据

- **WHEN** 创建 `ConditionContext` 实例
- **THEN** 包含 `capture`（ScreenCapture）、`rect`（WindowRect）、`rois`（dict）、`slots`（list）、`traps`（list）、`state`（dict）、`multi_frame`（dict）等评估所需数据

### Requirement: eval_conditions 便捷函数

系统 SHALL 保留模块级 `eval_conditions` 便捷函数，兼容任务卡片中的接口定义，内部委托给 `ConditionEngine` 实例。

#### Scenario: 使用便捷函数评估条件

- **WHEN** 直接调用 `eval_conditions(conditions, capture, rect, rois, slots, traps, state)`
- **THEN** 内部创建 `ConditionEngine` 实例并执行评估，返回 `bool`

### Requirement: OCR 不可用时的降级

系统 SHALL 在 OCR 引擎不可用时（`read_wave`/`read_resource` 返回 None）对条件评估采取保守策略。

#### Scenario: OCR 返回 None

- **WHEN** `read_resource` 返回 `None`（OCR 不可用或识别失败）
- **THEN** `resource_gte` 条件返回 `False`（资源未知时不应执行消耗资源的动作）

#### Scenario: read_wave 返回 None

- **WHEN** `read_wave` 返回 `None`
- **THEN** `wave_eq` 和 `wave_gte` 条件返回 `False`（波次未知时不应执行波次相关动作）

## MODIFIED Requirements

### Requirement: engine/__init__.py 导出更新

`engine/__init__.py` SHALL 新增导出 `ConditionEngine` 和 `ConditionContext`。
