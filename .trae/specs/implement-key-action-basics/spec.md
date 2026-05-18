# T07 - 按键动作基础 Spec

## Why

自动化执行器需要底层按键/鼠标操作原语来模拟玩家输入（按键、点击、拖拽），以及一个动作调度入口 `execute_action` 供上层波次循环调用。T07 是 P5（按 O 打开地图）、P8（放置陷阱）、P9（升级陷阱）等所有动作执行的基础，没有这些原语，后续 T08/T09/T10 均无法工作。

## What Changes

- 在 `automation-executor/src/td_executor/engine/action.py` 中实现按键/鼠标操作原语：`press_key`、`click_at`、`drag`
- 实现 `ensure_map_open`，调用 `VisionDetector.is_map_ui_open()` 检测地图界面状态，未打开则按 O 键
- 实现 `execute_action` 调度入口，T07 阶段仅处理 `type="log"`，其余类型留待 T10 扩展
- 使用 `pynput` 实现键盘模拟（press/hold），使用 `pyautogui` 实现鼠标操作（click/drag）
- 两个库不可用时优雅降级，打印 warning 并抛出 `RuntimeError`
- 更新 `engine/__init__.py` 导出新增公共类型

## Impact

- Affected specs: T08（地图导航依赖 `drag` 和 `ensure_map_open`）、T10（动作执行完整流程依赖 `execute_action` 调度入口）
- Affected code: `automation-executor/src/td_executor/engine/action.py`（主要修改）、`automation-executor/src/td_executor/engine/__init__.py`（导出更新）
- 新增测试: `automation-executor/tests/test_action.py`

## ADDED Requirements

### Requirement: 按键模拟 press_key

系统 SHALL 提供 `press_key(key: str, hold_ms: int = 0)` 函数，模拟键盘按键操作。

- 使用 `pynput.keyboard.Controller` 实现按键按下与释放
- `hold_ms == 0` 时为短按（press + release），`hold_ms > 0` 时为长按（press → sleep → release）
- `key` 参数支持单字符键（如 `"o"`, `"1"`, `"2"`）和特殊键名（如 `"enter"`, `"space"`, `"esc"`）
- 特殊键名通过 `pynput.keyboard.Key` 枚举映射处理
- `pynput` 不可用时，打印 warning 日志并抛出 `RuntimeError`

#### Scenario: 短按按键
- **WHEN** 调用 `press_key("o")`
- **THEN** 模拟按下 O 键后立即释放，`hold_ms` 默认为 0

#### Scenario: 长按按键
- **WHEN** 调用 `press_key("2", hold_ms=4000)`
- **THEN** 模拟按下 2 键，等待 4000ms 后释放

#### Scenario: 特殊按键
- **WHEN** 调用 `press_key("enter")`
- **THEN** 通过 `pynput.keyboard.Key.enter` 映射，正确模拟 Enter 键

#### Scenario: pynput 不可用
- **WHEN** `pynput` 未安装或导入失败
- **THEN** 打印 warning 日志，抛出 `RuntimeError`，不崩溃

### Requirement: 鼠标点击 click_at

系统 SHALL 提供 `click_at(x: int, y: int, button: str = "left")` 函数，在屏幕绝对坐标处点击。

- 使用 `pyautogui.click()` 实现鼠标点击
- `button` 参数支持 `"left"` 和 `"right"`
- 点击前不移动鼠标（使用 `pyautogui.click(x, y)` 直接点击目标坐标）
- `pyautogui` 不可用时，打印 warning 日志并抛出 `RuntimeError`

#### Scenario: 左键点击
- **WHEN** 调用 `click_at(960, 540)`
- **THEN** 在屏幕坐标 (960, 540) 处执行左键点击

#### Scenario: 右键点击
- **WHEN** 调用 `click_at(960, 540, button="right")`
- **THEN** 在屏幕坐标 (960, 540) 处执行右键点击

#### Scenario: pyautogui 不可用
- **WHEN** `pyautogui` 未安装或导入失败
- **THEN** 打印 warning 日志，抛出 `RuntimeError`，不崩溃

### Requirement: 拖拽操作 drag

系统 SHALL 提供 `drag(from_x: int, from_y: int, to_x: int, to_y: int, duration_ms: int = 600)` 函数，从一点拖拽到另一点。

- 使用 `pyautogui.moveTo()` + `pyautogui.mouseDown()` + `pyautogui.moveTo()` + `pyautogui.mouseUp()` 实现拖拽
- `duration_ms` 控制拖拽过程的持续时间（毫秒），转换为秒传给 pyautogui
- 默认使用左键拖拽
- `pyautogui` 不可用时，打印 warning 日志并抛出 `RuntimeError`

#### Scenario: 默认拖拽
- **WHEN** 调用 `drag(100, 200, 300, 400)`
- **THEN** 鼠标从 (100, 200) 拖拽到 (300, 400)，持续 600ms

#### Scenario: 自定义时长拖拽
- **WHEN** 调用 `drag(100, 200, 300, 400, duration_ms=1000)`
- **THEN** 鼠标从 (100, 200) 拖拽到 (300, 400)，持续 1000ms

### Requirement: 确保地图界面打开 ensure_map_open

系统 SHALL 提供 `ensure_map_open(capture, rect, rois)` 函数，确保游戏地图界面已打开。

- 创建 `VisionDetector` 实例，调用 `is_map_ui_open()` 检测当前是否在地图界面
- 如果地图界面未打开，调用 `press_key("o")` 打开地图
- 等待 `MAP_OPEN_WAIT_MS`（默认 800ms）后再次检测
- 最多重试 `MAP_OPEN_MAX_RETRIES`（默认 3）次
- 全部重试失败后打印 warning 并返回 `False`
- 地图已打开时直接返回 `True`

#### Scenario: 地图已打开
- **WHEN** 调用 `ensure_map_open(capture, rect, rois)` 且地图界面已打开
- **THEN** 返回 `True`，不执行任何按键操作

#### Scenario: 地图未打开，按 O 后成功打开
- **WHEN** 地图界面未打开
- **THEN** 按 O 键，等待后再次检测，地图打开后返回 `True`

#### Scenario: 多次重试后仍无法打开
- **WHEN** 按 O 键 3 次后地图界面仍未打开
- **THEN** 打印 warning 日志，返回 `False`

### Requirement: 动作调度入口 execute_action

系统 SHALL 提供 `execute_action(action: dict, context: dict) -> dict` 函数，作为单个波次动作的调度入口。

- 根据 `action["type"]` 分发到对应处理逻辑
- T07 阶段仅实现 `type="log"` 的处理：打印日志消息，返回 `{"success": True, "skipped": False}`
- 其他类型（`place_trap`, `upgrade_trap`, `remove_trap`, `pan_to_region`）暂不实现，返回 `{"success": False, "skipped": False, "error": "not implemented: <type>"}`
- `context` 字典包含运行时上下文：`capture`, `rect`, `rois`, `slots`, `traps`, `state`, `detector` 等，T07 阶段 `log` 类型不依赖 context

#### Scenario: 执行 log 动作
- **WHEN** 调用 `execute_action({"type": "log", "message": "第1波布防完成"}, context)`
- **THEN** 打印消息 `"第1波布防完成"`，返回 `{"success": True, "skipped": False}`

#### Scenario: 未实现的动作类型
- **WHEN** 调用 `execute_action({"type": "place_trap", ...}, context)`
- **THEN** 返回 `{"success": False, "skipped": False, "error": "not implemented: place_trap"}`

#### Scenario: 未知动作类型
- **WHEN** 调用 `execute_action({"type": "unknown"}, context)`
- **THEN** 打印 warning 日志，返回 `{"success": False, "skipped": False, "error": "unknown action type: unknown"}`

### Requirement: 输入库优雅降级

系统 SHALL 在 `pynput` 或 `pyautogui` 不可用时优雅降级。

- 模块级别使用 `try/except ImportError` 检测库可用性
- 设置模块级标志 `_PYNPUT_AVAILABLE` 和 `_PYAUTOGUI_AVAILABLE`
- 不可用时在首次调用相关函数时打印 warning 日志并抛出 `RuntimeError`
- 不在模块导入时崩溃

#### Scenario: pynput 可用
- **WHEN** `pynput` 已安装
- **THEN** `press_key` 正常工作

#### Scenario: pynput 不可用
- **WHEN** `pynput` 未安装
- **THEN** 调用 `press_key` 时打印 warning 并抛出 `RuntimeError`

#### Scenario: pyautogui 可用
- **WHEN** `pyautogui` 已安装
- **THEN** `click_at` 和 `drag` 正常工作

#### Scenario: pyautogui 不可用
- **WHEN** `pyautogui` 未安装
- **THEN** 调用 `click_at` 或 `drag` 时打印 warning 并抛出 `RuntimeError`

## MODIFIED Requirements

### Requirement: engine 包导出

`td_executor.engine.__init__` SHALL 导出 `press_key`, `click_at`, `drag`, `ensure_map_open`, `execute_action` 函数，供外部模块直接 `from td_executor.engine import ...` 使用。
