# 后台执行与 map_ui 检测优化 Spec

## Why

当前执行器存在三个问题：1) `ensure_map_open` 硬性要求 `rois.map_ui_indicator`，用户脚本不提供时直接失败；2) 连接窗口后 GUI 仍然缩小；3) 执行器使用 pyautogui/pynput 前台模拟输入，必须占用桌面，用户无法做其他操作。

## What Changes

- `ensure_map_open` 和 `is_map_ui_open` 改为可选检测：缺少 `map_ui_indicator` 时跳过检测，默认认为地图已打开
- 连接窗口时确保不触发焦点转移：overlay 使用 `SW_SHOWNOACTIVATE`，`find_game_window` 不调用 `focus_window`
- **BREAKING**: 将鼠标键盘输入从前台模拟（pyautogui/pynput）改为后台发送（ctypes SendMessage/PostMessage），实现真正的后台执行

## Impact

- Affected specs: `add-executor-gui`、`add-execution-overlay`
- Affected code:
  - `automation-executor/src/td_executor/engine/action.py`（click_at/press_key 改为后台发送）
  - `automation-executor/src/td_executor/vision/detector.py`（is_map_ui_open 容错）
  - `automation-executor/src/td_executor/ui/executor_bridge.py`（移除 focus_window 调用）
  - `automation-executor/src/td_executor/ui/app.py`（连接窗口不 focus）
  - `automation-executor/src/td_executor/runtime/window.py`（新增 send_click/send_key 后台函数）

## ADDED Requirements

### Requirement: 后台鼠标点击

系统 SHALL 通过 Win32 `SendMessage`/`PostMessage` 向目标窗口发送鼠标消息，实现后台点击，不占用桌面焦点。

- 新增 `runtime/input.py` 模块，实现 `send_click(hwnd, x, y, button="left")` 函数
- `x, y` 为相对于目标窗口客户区的坐标
- 使用 `PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(x, y))` + `PostMessageW(hwnd, WM_LBUTTONUP, 0, MAKELPARAM(x, y))` 发送点击
- 右键使用 `WM_RBUTTONDOWN`/`WM_RBUTTONUP`
- 非 Windows 平台降级为 pyautogui 前台点击
- `click_at` 函数改为优先使用后台发送，传入 `hwnd` 参数

#### Scenario: 后台左键点击
- **WHEN** 调用 `send_click(hwnd, 100, 200)`
- **THEN** 向 hwnd 窗口发送 `WM_LBUTTONDOWN` + `WM_LBUTTONUP` 消息，坐标 (100, 200)

#### Scenario: 非 Windows 平台降级
- **WHEN** 在 Linux 上调用 `send_click`
- **THEN** 降级为 pyautogui 前台点击

### Requirement: 后台键盘输入

系统 SHALL 通过 Win32 `SendMessage`/`PostMessage` 向目标窗口发送键盘消息，实现后台按键，不占用桌面焦点。

- 在 `runtime/input.py` 中实现 `send_key(hwnd, key, hold_ms=0)` 函数
- 普通字符键：`PostMessageW(hwnd, WM_KEYDOWN, vk_code, lParam)` + `PostMessageW(hwnd, WM_KEYUP, vk_code, lParam)`
- 特殊键（如 O 键打开地图）：使用 `VkKeyScanW` 获取虚拟键码
- `hold_ms > 0` 时，`KEYDOWN` 和 `KEYUP` 之间 sleep 指定时间
- 非 Windows 平台降级为 pynput 前台按键
- `press_key` 函数改为优先使用后台发送，传入 `hwnd` 参数

#### Scenario: 后台按键
- **WHEN** 调用 `send_key(hwnd, "o")`
- **THEN** 向 hwnd 窗口发送 `WM_KEYDOWN` + `WM_KEYUP` 消息，虚拟键码为 'O'

#### Scenario: 后台按住按键
- **WHEN** 调用 `send_key(hwnd, "1", hold_ms=4000)`
- **THEN** 发送 `WM_KEYDOWN`，等待 4000ms，再发送 `WM_KEYUP`

### Requirement: map_ui_indicator 可选检测

系统 SHALL 在 `rois` 中缺少 `map_ui_indicator` 时跳过地图 UI 检测，而非报错失败。

- `is_map_ui_open` 在缺少 `map_ui_indicator` 时返回 `True`（默认认为地图已打开）
- `ensure_map_open` 在 `is_map_ui_open` 返回 True 时直接通过
- 日志级别从 `warning` 降为 `info`

#### Scenario: 缺少 map_ui_indicator
- **WHEN** `rois` 中没有 `map_ui_indicator`
- **THEN** `is_map_ui_open` 返回 True，`ensure_map_open` 直接通过

#### Scenario: 有 map_ui_indicator
- **WHEN** `rois` 中有 `map_ui_indicator`
- **THEN** 正常执行模板匹配检测

### Requirement: 连接窗口不影响 GUI 焦点

系统 SHALL 确保连接窗口时 GUI 主窗口不会缩小或失焦。

- `executor_bridge._execute_script` 不再调用 `focus_window`（后台执行不需要前台焦点）
- `connect_window`/`connect_window_by_hwnd` 不调用 `focus_window`
- overlay `show()` 使用 `SW_SHOWNOACTIVATE` (值为 4) 而非 `SW_SHOW`
- 连接完成后调用 `self.focus_force()` 确保 GUI 保持焦点

#### Scenario: 连接窗口后 GUI 不缩小
- **WHEN** 用户连接游戏窗口
- **THEN** GUI 主窗口尺寸和焦点保持不变

#### Scenario: 后台执行时用户可做其他操作
- **WHEN** 执行器正在后台运行脚本
- **THEN** 用户可以切换到其他窗口操作，不影响脚本执行

## MODIFIED Requirements

### Requirement: 执行前聚焦游戏窗口（来自 add-execution-overlay）

- ~~执行前调用 `focus_window(rect.hwnd)`~~ → 移除，后台执行不需要聚焦
- 保留窗口有效性检查 `is_window_valid`

### Requirement: 脚本管理与启动（来自 add-executor-gui）

- `click_at` 和 `press_key` 改为后台发送消息
- 执行器不再需要游戏窗口在前台

## REMOVED Requirements

无
