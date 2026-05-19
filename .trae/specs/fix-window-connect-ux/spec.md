# 窗口连接交互优化 Spec

## Why

当前"连接窗口"功能存在三个体验问题：1) 点击连接后 GUI 窗口会瞬间缩小（因为 `focus_window` 将焦点抢到游戏窗口，tkinter 窗口失去焦点后可能触发尺寸重算）；2) 连接后无法断开，只能通过"重置"按钮间接断开；3) 只能按关键字搜索，无法看到所有匹配进程并选择。

## What Changes

- 修复 GUI 窗口缩小问题：连接窗口时不再调用 `focus_window`，避免焦点转移导致 GUI 窗口缩小
- 新增"断开连接"按钮：连接成功后，"连接窗口"按钮变为"断开连接"，点击可断开连接
- 新增窗口选择对话框：点击"连接窗口"后，弹出对话框列出所有匹配的窗口进程，用户选择其中一个连接

## Impact

- Affected specs: `add-executor-gui`（脚本管理与启动需求）
- Affected code:
  - `automation-executor/src/td_executor/ui/script_tab.py`（连接/断开按钮、选择对话框）
  - `automation-executor/src/td_executor/ui/app.py`（connect_window 不再 focus）
  - `automation-executor/src/td_executor/runtime/window.py`（新增 list_windows 函数）

## ADDED Requirements

### Requirement: 窗口列表枚举

系统 SHALL 提供 `list_windows` 函数，枚举所有可见窗口，返回窗口句柄和标题列表。

- 在 `td_executor.runtime.window` 中新增 `list_windows(title_keyword: str = "") -> list[dict]` 函数
- 返回列表中每项包含 `hwnd`（int）和 `title`（str）
- `title_keyword` 为空时返回所有可见窗口，非空时返回标题包含关键字的窗口
- Windows 平台使用 ctypes 调用 `EnumWindows` + `GetWindowTextW`
- 非 Windows 平台返回空列表

#### Scenario: 列出所有窗口
- **WHEN** 调用 `list_windows()` 不传参数
- **THEN** 返回所有可见窗口的 hwnd 和 title 列表

#### Scenario: 按关键字过滤
- **WHEN** 调用 `list_windows("逆战")`
- **THEN** 仅返回标题包含"逆战"的可见窗口

### Requirement: 窗口选择对话框

系统 SHALL 在用户点击"连接窗口"时，弹出窗口选择对话框，列出所有匹配的窗口供用户选择。

- 点击"连接窗口"按钮后，弹出 `tkinter.Toplevel` 对话框
- 对话框标题为"选择游戏窗口"
- 对话框中包含一个 `ttk.Treeview` 列表，列包括：序号、窗口标题、句柄
- 列表自动填入根据标题关键字过滤的窗口
- 对话框底部有"连接"和"取消"两个按钮
- 选中一行后点击"连接"完成连接，点击"取消"关闭对话框
- 未选中任何行时"连接"按钮禁用
- 对话框为模态窗口（grab_set），阻止操作主窗口
- 对话框大小约 500x400，居中显示在主窗口上

#### Scenario: 有匹配窗口
- **WHEN** 用户点击"连接窗口"且存在匹配窗口
- **THEN** 弹出对话框显示匹配窗口列表，用户选择后点击"连接"完成连接

#### Scenario: 无匹配窗口
- **WHEN** 用户点击"连接窗口"且无匹配窗口
- **THEN** 弹出提示"未找到匹配的窗口进程"，不弹出选择对话框

#### Scenario: 取消选择
- **WHEN** 用户在对话框中点击"取消"
- **THEN** 关闭对话框，不改变连接状态

### Requirement: 断开连接功能

系统 SHALL 在窗口连接成功后提供"断开连接"按钮。

- 连接成功后，"连接窗口"按钮文本变为"断开连接"
- 点击"断开连接"后：清除已连接的窗口 rect、状态栏恢复为"窗口: 未连接"、画面标签页清除截图、按钮文本恢复为"连接窗口"
- 执行器运行中时，"断开连接"按钮禁用（防止运行中断开导致异常）

#### Scenario: 连接后断开
- **WHEN** 用户已连接窗口且执行器未运行
- **THEN** 点击"断开连接"后清除连接状态，按钮恢复为"连接窗口"

#### Scenario: 运行中禁止断开
- **WHEN** 执行器正在运行
- **THEN** "断开连接"按钮禁用，无法点击

### Requirement: 连接窗口不导致 GUI 缩小

系统 SHALL 确保连接游戏窗口时不会导致 GUI 主窗口缩小或失焦。

- `connect_window` 方法不再调用 `focus_window`
- 连接窗口时仅获取窗口 rect 信息，不改变任何窗口的焦点状态

#### Scenario: 连接窗口后 GUI 尺寸不变
- **WHEN** 用户点击"连接窗口"并成功连接
- **THEN** GUI 主窗口尺寸和焦点保持不变

## MODIFIED Requirements

### Requirement: 脚本管理与启动（来自 add-executor-gui）

"连接窗口"按钮行为修改：
- 点击后弹出窗口选择对话框，而非直接连接第一个匹配窗口
- 连接成功后按钮变为"断开连接"
- 运行中时"断开连接"按钮禁用
