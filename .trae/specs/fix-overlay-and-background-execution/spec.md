# 修复 Overlay 与后台执行 Spec

## Why

当前实现存在三个未解决的严重问题：

1. **GUI 缩小问题**：点击连接窗口后 GUI 界面仍然缩小，原因是 overlay 创建过程中短暂抢占焦点，且 `focus_force()` 调用时机错误（应先于 `show()` 调用）
2. **后台执行失效**：`send_click` 发送的坐标转换有误——当前代码用 overlay 窗口的客户区坐标，而 PostMessage 需要相对于**游戏窗口**的客户区坐标
3. **Overlay 不同步**：游戏窗口移动或调整大小时，overlay 不会跟随更新

参考 ok-script 框架的核心方案：
- overlay 位置随目标窗口实时同步（通过 Qt 信号槽机制或定时轮询）
- 点击坐标通过 `ClientToScreen → ScreenToClient` 双重转换精确定位
- overlay 创建后不抢占焦点（SW_SHOWNOACTIVATE + focus_force 提前调用）

## What Changes

### 1. GUI 不缩小修复
- `connect_window_by_hwnd` 中，先 `self.focus_force()`，再 `self._overlay.show(rect.hwnd)`
- `overlay.show()` 内部：先 `SetWindowPos(..., SWP_NOZORDER | SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)` 将 overlay 移到目标窗口位置，再 `ShowWindow(..., SW_SHOWNOACTIVATE)`

### 2. 后台点击坐标转换修复
- `send_click` 需要将"游戏窗口客户区坐标"通过 `ClientToScreen(game_hwnd)` → `ScreenToClient(target_hwnd)` 转换为目标子窗口的坐标
- 参考 `PostMessageInteraction.update_mouse_pos`：计算游戏窗口的屏幕偏移，传入的 x/y 加上 rect.left/rect.top 作为屏幕坐标，再转换到目标窗口

### 3. Overlay 位置同步
- 新增 `sync_overlay_position()` 方法，定时更新 overlay 位置（每 500ms 轮询）
- 同步使用 `GetWindowRect` 获取窗口最新位置和大小
- 窗口关闭或无效时自动隐藏 overlay

### 4. 开发模式（参考 ok-script OverlayWidget）
- `show_overlay_debug()` 显示红色边框（已实现，保持不变）
- `draw_click_marker` 显示点击位置（已实现，保持不变）
- `draw_key_info` 显示按键信息（已实现，保持不变）
- 新增：显示当前连接的窗口标题+hwnd + 操作日志（叠加在 overlay 左上角，半透明黑底白字）

## Impact

- Affected specs: `add-execution-overlay`、`add-background-execution`
- Affected code:
  - `runtime/input.py`（send_click 坐标转换修复）
  - `runtime/overlay.py`（show 顺序修复 + 位置同步）
  - `ui/app.py`（focus_force 顺序 + 同步定时器）

## ADDED Requirements

### Requirement: Overlay 不抢占 GUI 焦点

`connect_window_by_hwnd` 执行顺序：
1. `self.focus_force()` 先调用
2. `self._overlay.show(rect.hwnd)` 后调用

`overlay.show()` 内部：
1. `SetWindowPos` 先将 overlay 移到目标窗口位置（SWP_NOACTIVATE）
2. `ShowWindow(..., SW_SHOWNOACTIVATE)` 不激活窗口

#### Scenario: 连接窗口后 GUI 尺寸不变
- **WHEN** 用户点击连接游戏窗口
- **THEN** GUI 主窗口尺寸和焦点保持不变

### Requirement: 精确坐标转换后台点击

`send_click(hwnd, x, y, button)` 实现：
1. 用 `ClientToScreen(game_hwnd, (x, y))` 将游戏窗口客户区坐标转为屏幕坐标
2. 如果目标 hwnd 与游戏 hwnd 不同，用 `ScreenToClient(target_hwnd, (screen_x, screen_y))` 转换
3. `MAKELPARAM(local_x, local_y)` 打包，发送 PostMessage

#### Scenario: 点击陷阱格子
- **WHEN** 陷阱格子坐标为 (835, 432)（游戏窗口客户区坐标）
- **THEN** PostMessage 发送的 lparam 坐标为相对于目标窗口客户区的正确坐标

### Requirement: Overlay 随窗口同步

OverlayWindow 新增：
- `_sync_timer_id` 定时器，每 500ms 检查窗口位置
- `_sync_position()` 方法：用 `GetWindowRect` 获取窗口最新 rect
- 如果窗口 rect 变化或窗口无效，自动调用 `hide()`
- `show()` 成功后将 rect 存入 `_last_rect` 供 `_sync_position` 使用

#### Scenario: 游戏窗口移动后 overlay 跟随
- **WHEN** 游戏窗口被拖动到新位置
- **THEN** overlay 在 500ms 内移动到新位置

### Requirement: 开发模式显示窗口信息

Overlay 叠加显示：
- 窗口标题 + hwnd（如 `逆战 (hwnd=12345)`）
- 最近 N 条操作日志（每条一行，超出后截断）
- 字体：微软雅黑 12pt，颜色：白字黑底

## REMOVED Requirements

无

## MODIFIED Requirements

### Requirement: send_click 后台点击（来自 add-background-execution）

- 移除：将 rect_left/rect_top 相减的错误逻辑
- 改为：`ClientToScreen` → `ScreenToClient` 双重坐标转换

### Requirement: Overlay 同步（来自 add-execution-overlay）

- 新增：`_sync_position()` 定时更新 overlay 位置
