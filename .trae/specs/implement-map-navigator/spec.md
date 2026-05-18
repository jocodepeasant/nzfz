# T08 地图导航 Spec

## Why

放置/升级/拆除陷阱前需要先导航到对应的地图区域（region）。地图导航模块负责将视野从初始位置（origin）拖拽到目标区域，通过执行 region 配置中的 `enter_actions`（一系列 `pan_map` 拖拽动作）实现。这是动作执行流程（T10）中"进入 slot 所属 region"步骤的核心依赖。

## What Changes

- 替换 `automation-executor/src/td_executor/engine/navigator.py` 的占位实现，完成完整的地图导航功能
- 实现 `go_to_origin`：关闭地图再重新打开，回到初始视野
- 实现 `pan_to_region`：先回 origin，再执行 region 的 enter_actions 拖拽序列
- 实现 `execute_pan_action`：执行单个 pan_map 动作（方向/距离计算 + repeat 重复 + 等待）
- 实现 `calculate_pan_endpoints`：根据方向和距离比例计算拖拽起止像素坐标
- 更新 `engine/__init__.py` 导出新类型

## Impact

- Affected specs: T09（格子定位）将调用 `pan_to_region` 导航到 slot 所属区域；T10（动作执行完整流程）将调用导航功能
- Affected code:
  - `automation-executor/src/td_executor/engine/navigator.py` — 主要修改文件
  - `automation-executor/src/td_executor/engine/__init__.py` — 新增导出
- 依赖模块（只读使用）:
  - `td_executor.engine.action` → `press_key`, `drag`, `ensure_map_open`
  - `td_executor.runtime.window` → `WindowRect`
  - `td_executor.runtime.capture` → `ScreenCapture`

## ADDED Requirements

### Requirement: go_to_origin 回到初始视野

系统 SHALL 提供 `go_to_origin` 函数，通过关闭地图再重新打开的方式回到初始视野。

#### Scenario: 成功回到 origin

- **WHEN** `go_to_origin` 被调用，且地图界面已打开
- **THEN** 按 O 键关闭地图 → 等待 `map_close_wait_ms` → 按 O 键重新打开地图 → 等待 `map_open_wait_ms` → 调用 `ensure_map_open` 验证地图已打开 → 返回 `True`

#### Scenario: 地图未打开时先打开地图

- **WHEN** `go_to_origin` 被调用，且地图界面未打开
- **THEN** 直接调用 `ensure_map_open` 打开地图 → 返回结果

#### Scenario: 重新打开地图后验证失败

- **WHEN** `go_to_origin` 被调用，但重新打开后 `ensure_map_open` 返回 False
- **THEN** 打印 warning 日志，返回 `False`

### Requirement: pan_to_region 导航到指定区域

系统 SHALL 提供 `pan_to_region` 函数，先回到 origin 视野，再执行目标 region 的 `enter_actions` 拖拽序列。

#### Scenario: 成功导航到区域

- **WHEN** `pan_to_region` 被调用，且 region_id 在 regions 列表中存在
- **THEN** 先调用 `go_to_origin` 回到初始视野 → 按顺序执行 region 的 `enter_actions` → 返回 `True`

#### Scenario: region_id 不存在

- **WHEN** `pan_to_region` 被调用，且 region_id 在 regions 列表中不存在
- **THEN** 打印 warning 日志，返回 `False`

#### Scenario: region 为 origin（无需拖拽）

- **WHEN** `pan_to_region` 被调用，且 region_id 为 origin（enter_actions 为空）
- **THEN** 只调用 `go_to_origin`，不执行任何拖拽，返回 `True`

### Requirement: execute_pan_action 执行单个拖拽动作

系统 SHALL 提供 `execute_pan_action` 函数，执行单个 `pan_map` 动作配置。

#### Scenario: 单次拖拽

- **WHEN** `execute_pan_action` 被调用，且 `repeat=1`
- **THEN** 计算拖拽起止点 → 调用 `drag` 执行拖拽 → 等待 `wait_after_pan_ms` → 返回 `True`

#### Scenario: 重复拖拽

- **WHEN** `execute_pan_action` 被调用，且 `repeat=3`
- **THEN** 执行 3 次拖拽，每次拖拽后等待 `wait_after_pan_ms`

#### Scenario: drag 调用失败

- **WHEN** `execute_pan_action` 被调用，但 `drag` 抛出异常（如 pyautogui 不可用）
- **THEN** 捕获异常，打印 warning 日志，返回 `False`

### Requirement: calculate_pan_endpoints 计算拖拽端点

系统 SHALL 提供 `calculate_pan_endpoints` 函数，根据方向和距离比例计算拖拽起止像素坐标。

#### Scenario: 向左拖拽

- **WHEN** `direction="left"`, `distance_ratio=0.3`
- **THEN** 起点为窗口中心偏右位置，终点向左偏移 `window_width * distance_ratio` 像素

#### Scenario: 向右拖拽

- **WHEN** `direction="right"`, `distance_ratio=0.3`
- **THEN** 起点为窗口中心偏左位置，终点向右偏移 `window_width * distance_ratio` 像素

#### Scenario: 向上拖拽

- **WHEN** `direction="up"`, `distance_ratio=0.3`
- **THEN** 起点为窗口中心偏下位置，终点向上偏移 `window_height * distance_ratio` 像素

#### Scenario: 向下拖拽

- **WHEN** `direction="down"`, `distance_ratio=0.3`
- **THEN** 起点为窗口中心偏上位置，终点向下偏移 `window_height * distance_ratio` 像素

#### Scenario: 未知方向

- **WHEN** `direction` 不是 left/right/up/down 之一
- **THEN** 打印 warning 日志，返回 `None`

### Requirement: 拖拽方向映射细节

拖拽起点应从窗口中心附近开始，以确保拖拽操作在地图内容区域内执行。具体计算规则：

- **水平拖拽**：起点 x = `window_left + window_width * 0.5`，起点 y = `window_top + window_height * 0.5`
  - left: 终点 x = 起点 x - `window_width * distance_ratio`
  - right: 终点 x = 起点 x + `window_width * distance_ratio`
  - 终点 y = 起点 y
- **垂直拖拽**：起点同上
  - up: 终点 y = 起点 y - `window_height * distance_ratio`
  - down: 终点 y = 起点 y + `window_height * distance_ratio`
  - 终点 x = 起点 x

### Requirement: NavigatorConfig 配置数据类

系统 SHALL 提供 `NavigatorConfig` 数据类，封装导航相关的运行时配置参数。

#### Scenario: NavigatorConfig 默认值

- **WHEN** 创建 `NavigatorConfig` 实例不传参数
- **THEN** `map_close_wait_ms=500`, `map_open_wait_ms=800`, `wait_after_pan_ms` 从 runtime dict 读取（默认 800）

### Requirement: pyautogui/pynput 不可用时优雅降级

系统 SHALL 在 `drag` 或 `press_key` 调用抛出 RuntimeError（库不可用）时优雅处理。

#### Scenario: drag 不可用

- **WHEN** `execute_pan_action` 调用 `drag` 抛出 RuntimeError
- **THEN** 捕获异常，打印 warning 日志，返回 `False`

#### Scenario: press_key 不可用

- **WHEN** `go_to_origin` 调用 `press_key` 抛出 RuntimeError
- **THEN** 捕获异常，打印 warning 日志，返回 `False`

## MODIFIED Requirements

### Requirement: engine/__init__.py 导出更新

`engine/__init__.py` SHALL 新增导出 `go_to_origin`、`pan_to_region`、`execute_pan_action`、`calculate_pan_endpoints`、`NavigatorConfig`。
