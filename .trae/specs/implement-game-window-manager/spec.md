# 游戏窗口管理器 Spec

## Why
automation-executor 当前所有运行时能力（屏幕采集、OCR、动作执行）均依赖游戏窗口定位，但 `runtime/window.py` 的 `find_game_window()` 仅抛出 `NotImplementedError`。没有窗口管理，后续 P3~P13 的所有功能都无法运转。

## What Changes
- 实现 `find_game_window()`：通过窗口标题定位游戏窗口，返回窗口位置和尺寸
- 实现 `focus_window()`：将游戏窗口置顶并激活
- 实现 `get_window_rect()`：获取窗口客户区位置和尺寸（用于比例坐标转换）
- 实现 `is_window_valid()`：校验窗口是否仍然存在且可见
- 扩展 `GameState`：添加窗口相关状态字段（window_handle, window_rect, is_focused）
- 更新 `cli.py` 的 `run` 命令：在 dry-run 之外支持真实运行模式的前置窗口检测
- 添加 Windows 平台实现（pywin32），Linux/macOS 提供降级方案

## Impact
- Affected specs: P2（游戏窗口识别）— 设计文档 10.2 节优先级第 2 项
- Affected code:
  - `runtime/window.py` — 主要变更
  - `state.py` — GameState 扩展
  - `cli.py` — run 命令更新
  - `runtime/coordinates.py` — 将使用 get_window_rect() 的返回值

## ADDED Requirements

### Requirement: 游戏窗口定位
系统 SHALL 提供通过窗口标题关键字定位游戏窗口的能力。

#### Scenario: 找到游戏窗口
- **WHEN** 调用 `find_game_window(title_keyword="逆战")`
- **AND** 存在标题包含关键字的窗口
- **THEN** 返回窗口句柄和窗口矩形 `{hwnd, left, top, width, height}`

#### Scenario: 未找到游戏窗口
- **WHEN** 调用 `find_game_window(title_keyword="逆战")`
- **AND** 不存在标题包含关键字的窗口
- **THEN** 返回 `None`
- **AND** 记录 warning 日志

### Requirement: 窗口焦点管理
系统 SHALL 提供将游戏窗口置顶激活的能力。

#### Scenario: 激活窗口成功
- **WHEN** 调用 `focus_window(hwnd)`
- **AND** 窗口存在且可操作
- **THEN** 窗口被置顶并获得焦点
- **AND** 返回 `True`

#### Scenario: 窗口已最小化
- **WHEN** 调用 `focus_window(hwnd)`
- **AND** 窗口处于最小化状态
- **THEN** 先恢复窗口再置顶
- **AND** 返回 `True`

### Requirement: 窗口客户区矩形
系统 SHALL 提供获取窗口客户区（不含标题栏和边框）位置和尺寸的能力。

#### Scenario: 获取客户区成功
- **WHEN** 调用 `get_window_rect(hwnd)`
- **AND** 窗口存在
- **THEN** 返回客户区矩形 `{left, top, width, height}`
- **AND** 该矩形可直接用于 `ratio_to_pixel()` 的坐标转换

### Requirement: 窗口有效性校验
系统 SHALL 提供校验窗口是否仍然存在且可见的能力。

#### Scenario: 窗口有效
- **WHEN** 调用 `is_window_valid(hwnd)`
- **AND** 窗口存在且可见
- **THEN** 返回 `True`

#### Scenario: 窗口已关闭
- **WHEN** 调用 `is_window_valid(hwnd)`
- **AND** 窗口已被关闭
- **THEN** 返回 `False`

### Requirement: GameState 窗口状态扩展
系统 SHALL 在 GameState 中维护窗口相关状态。

#### Scenario: 窗口状态初始化
- **WHEN** 成功定位游戏窗口
- **THEN** GameState 记录 window_handle、window_rect、is_focused 字段

### Requirement: CLI run 命令窗口检测
系统 SHALL 在 `run` 命令执行前自动检测游戏窗口。

#### Scenario: 窗口检测成功
- **WHEN** 执行 `td-executor run script.json`（非 dry-run）
- **AND** 成功定位游戏窗口
- **THEN** 打印窗口信息并继续

#### Scenario: 窗口检测失败
- **WHEN** 执行 `td-executor run script.json`（非 dry-run）
- **AND** 未找到游戏窗口
- **THEN** 打印错误提示并以 exit code 1 退出

### Requirement: 跨平台降级
系统 SHALL 在 Windows 上使用 pywin32 实现，在非 Windows 平台提供基于 mss 的降级方案。

#### Scenario: Windows 平台
- **WHEN** 运行在 Windows 上
- **THEN** 使用 pywin32 的 win32gui / win32con API 实现

#### Scenario: 非 Windows 平台
- **WHEN** 运行在 Linux/macOS 上
- **THEN** 使用 mss 获取屏幕尺寸，窗口定位返回全屏区域作为降级方案
- **AND** 打印 warning 提示功能受限
