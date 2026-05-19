# 执行目标窗口与调试可视化 Spec

## Why

当前执行器使用 pyautogui 进行屏幕绝对坐标点击，但未确保游戏窗口在前台，导致操作落在其他窗口上。同时缺少连接窗口的可视标识和调试时的操作可视化，用户无法直观确认操作是否在正确窗口执行。

## What Changes

- 执行动作前将游戏窗口调到前台（focus_window），确保操作落在目标窗口
- 连接窗口后在游戏窗口上绘制红色边框覆盖层，标识已连接的窗口
- Debug 模式下在游戏窗口上实时可视化操作（点击位置、按键、持续时间等）
- 新增 `runtime/overlay.py` 模块实现窗口覆盖层绘制

## Impact

- Affected specs: `add-executor-gui`（执行流程）
- Affected code:
  - `automation-executor/src/td_executor/runtime/window.py`（focus_window 已有）
  - `automation-executor/src/td_executor/runtime/overlay.py`（新增）
  - `automation-executor/src/td_executor/engine/action.py`（执行前 focus）
  - `automation-executor/src/td_executor/ui/executor_bridge.py`（执行前 focus、debug 模式）
  - `automation-executor/src/td_executor/ui/app.py`（连接/断开时管理 overlay）
  - `automation-executor/src/td_executor/ui/script_tab.py`（debug 模式开关）

## ADDED Requirements

### Requirement: 执行前聚焦游戏窗口

系统 SHALL 在执行脚本动作前将游戏窗口调到前台，确保鼠标键盘操作落在目标窗口上。

- `executor_bridge.py` 的 `_execute_script` 在开始执行波次前调用 `focus_window(rect.hwnd)`
- 每个波次开始前检查窗口是否仍然有效（`is_window_valid`），无效则停止执行
- 如果 `focus_window` 失败，记录警告但继续执行（某些游戏可能阻止前台切换）

#### Scenario: 执行前聚焦
- **WHEN** 执行器开始执行脚本
- **THEN** 先调用 `focus_window(rect.hwnd)` 将游戏窗口调到前台，再执行动作

#### Scenario: 窗口失效
- **WHEN** 执行过程中游戏窗口被关闭
- **THEN** 检测到窗口无效后停止执行，发出 ExecutionDoneEvent(result="error")

### Requirement: 连接窗口红色边框标识

系统 SHALL 在连接游戏窗口后，在目标窗口上绘制一个红色边框覆盖层，标识已连接的窗口。

- 新增 `runtime/overlay.py` 模块，实现 `WindowOverlay` 类
- `WindowOverlay` 使用 ctypes 调用 Win32 API 创建一个透明的分层窗口（`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST`），覆盖在游戏窗口客户区上方
- 红色边框宽度 3px，绘制在覆盖层窗口边缘
- 覆盖层窗口设置 `WS_EX_TRANSPARENT` 使鼠标点击穿透到下层游戏窗口
- 连接窗口时创建 overlay，断开连接时销毁 overlay
- 非 Windows 平台 overlay 功能不可用，不影响其他功能

#### Scenario: 连接后显示红色边框
- **WHEN** 用户成功连接游戏窗口
- **THEN** 在游戏窗口客户区上方显示红色边框覆盖层

#### Scenario: 断开后移除边框
- **WHEN** 用户断开窗口连接
- **THEN** 红色边框覆盖层被销毁

#### Scenario: 鼠标穿透
- **WHEN** 红色边框覆盖层显示中
- **THEN** 鼠标点击穿透覆盖层，正常操作游戏窗口

### Requirement: Debug 模式操作可视化

系统 SHALL 在 Debug 模式下在游戏窗口覆盖层上实时显示操作信息。

- 脚本标签页新增"调试模式"复选框
- Debug 模式开启时，覆盖层额外显示以下信息：
  - **点击位置**：在点击坐标处显示红色十字标记（持续 1.5 秒后消失）
  - **按键操作**：在窗口左上角显示最近按下的按键名称（持续 2 秒后消失）
  - **按键持续时间**：如果按键有 hold_ms，显示持续时间（如"按住 O 800ms"）
- 点击标记和按键文字通过定时器自动清除
- Debug 模式关闭时，覆盖层仅显示红色边框

#### Scenario: Debug 模式点击可视化
- **WHEN** Debug 模式开启且执行器执行 `click_at(x, y)`
- **THEN** 在游戏窗口覆盖层的 (x, y) 位置显示红色十字标记，1.5 秒后自动消失

#### Scenario: Debug 模式按键可视化
- **WHEN** Debug 模式开启且执行器执行 `press_key(key, hold_ms)`
- **THEN** 在游戏窗口左上角显示按键信息（如"按住 1 4000ms"），2 秒后自动消失

#### Scenario: Debug 模式关闭
- **WHEN** Debug 模式关闭
- **THEN** 覆盖层仅显示红色边框，不显示操作信息

## MODIFIED Requirements

### Requirement: 脚本管理与启动（来自 add-executor-gui）

- 执行器启动前自动聚焦游戏窗口
- 新增"调试模式"复选框，控制操作可视化
