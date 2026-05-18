# 执行器可视化界面 Spec

## Why

当前执行器仅提供 CLI 命令行交互，用户无法直观地监控执行进度、查看运行状态和游戏画面。需要一个桌面 GUI 可视化界面，让用户能够加载脚本、启动/停止执行、实时监控动作执行状态、查看游戏画面预览和运行报告，提升操作体验和调试效率。

## What Changes

- 新增 `automation-executor/src/td_executor/ui/` 包，包含 GUI 界面模块
- 使用 tkinter 实现（Python 标准库，无需额外依赖，跨平台兼容）
- 实现四个核心功能模块：执行监控面板、脚本管理与启动、运行报告查看、游戏画面预览
- 新增 CLI `gui` 命令入口
- 新增 `ui` 可选依赖组（Pillow 用于图片处理）

## Impact

- Affected specs: 无（新增独立模块，不影响现有引擎代码）
- Affected code: `automation-executor/src/td_executor/cli.py`（新增 gui 命令）、`automation-executor/pyproject.toml`（新增依赖）
- 新增代码: `automation-executor/src/td_executor/ui/` 包

## ADDED Requirements

### Requirement: GUI 主窗口

系统 SHALL 提供 `ExecutorApp` 主窗口类，作为可视化界面的顶层容器。

- 使用 tkinter 实现，窗口标题为 "TD Executor - 塔防自动化执行器"
- 窗口默认尺寸 1100x750，可调整大小
- 使用 ttk.Notebook 实现多标签页切换：监控、脚本、报告、画面
- 底部状态栏显示：当前状态（空闲/运行中/已停止）、游戏窗口信息、当前时间
- 窗口关闭时若正在执行，弹出确认对话框

#### Scenario: 启动 GUI
- **WHEN** 用户执行 `td-executor gui` 命令
- **THEN** 弹出主窗口，显示四个标签页和底部状态栏

#### Scenario: 运行中关闭窗口
- **WHEN** 执行器正在运行时用户关闭窗口
- **THEN** 弹出确认对话框 "执行器正在运行，确认退出？"

### Requirement: 执行监控面板

系统 SHALL 在"监控"标签页中提供实时执行状态监控。

- **动作列表**：使用 ttk.Treeview 显示当前波次的动作列表，列包括：序号、类型、名称、状态、重试次数、耗时
- **状态标识**：待执行（灰色）、执行中（蓝色）、成功（绿色）、失败（红色）、跳过（黄色）
- **进度条**：顶部显示当前波次进度（如 "波次 3/10"）和整体进度条
- **实时更新**：动作执行状态变化时实时更新列表，使用 tkinter.after 轮询机制
- **统计摘要**：右侧面板显示：总动作数、成功数、失败数、跳过数、运行时长

#### Scenario: 执行中监控
- **WHEN** 执行器正在运行
- **THEN** 监控面板实时更新动作状态，进度条显示当前波次进度

#### Scenario: 动作成功
- **WHEN** 某个动作执行成功
- **THEN** 该行动作状态列显示绿色 "✓ 成功"

#### Scenario: 动作失败
- **WHEN** 某个动作执行失败
- **THEN** 该行动作状态列显示红色 "✗ 失败"，重试次数列显示实际重试次数

### Requirement: 脚本管理与启动

系统 SHALL 在"脚本"标签页中提供脚本加载、校验和执行控制功能。

- **脚本选择**：文件选择按钮 + 路径输入框，选择 JSON 脚本文件
- **脚本校验**：点击"校验"按钮，调用 `validate_script_data` 校验脚本，结果显示在下方文本框
- **脚本预览**：校验通过后，在文本框中显示脚本摘要（地图名、波次数、动作总数、陷阱列表）
- **运行参数**：游戏窗口标题关键字输入框（默认 "逆战"）、dry-run 复选框
- **控制按钮**：启动（绿色）、停止（红色）、重置（灰色）
- **启动流程**：点击启动 → 校验脚本 → 定位游戏窗口 → 创建 ActionExecutor → 在子线程中执行
- **停止流程**：点击停止 → 设置停止标志 → 等待当前动作完成 → 停止执行

#### Scenario: 加载并校验脚本
- **WHEN** 用户选择脚本文件并点击"校验"
- **THEN** 调用 `validate_script_data`，校验通过显示绿色提示，失败显示红色错误列表

#### Scenario: 启动执行
- **WHEN** 用户点击"启动"按钮
- **THEN** 在子线程中创建 ActionExecutor 并执行脚本，监控面板自动切换到前台

#### Scenario: 停止执行
- **WHEN** 用户点击"停止"按钮
- **THEN** 设置停止标志，等待当前动作完成后停止

### Requirement: 运行报告查看

系统 SHALL 在"报告"标签页中提供历史运行报告查看功能。

- **报告列表**：左侧 ttk.Treeview 显示历史报告列表，列包括：时间、脚本名、结果、时长
- **报告详情**：右侧显示选中报告的详细信息
- **动作日志表格**：显示该次运行的所有动作日志，列包括：波次、类型、名称、状态、重试次数、错误信息
- **统计摘要**：显示总动作数、成功数、失败数、运行时长
- **导出功能**：点击"导出"按钮可将报告导出为 JSON 文件
- **报告存储**：运行完成后自动保存报告到 `reports/` 目录，文件名格式 `report_YYYYMMDD_HHMMSS.json`

#### Scenario: 查看历史报告
- **WHEN** 用户在报告列表中选择一条记录
- **THEN** 右侧显示该次运行的详细动作日志和统计摘要

#### Scenario: 导出报告
- **WHEN** 用户点击"导出"按钮
- **THEN** 弹出文件保存对话框，将报告保存为 JSON 文件

### Requirement: 游戏画面预览

系统 SHALL 在"画面"标签页中提供游戏窗口截图预览功能。

- **截图显示**：使用 tkinter Canvas 显示游戏窗口截图
- **自动刷新**：执行期间每隔 2 秒自动刷新截图
- **手动刷新**：提供"刷新截图"按钮手动触发
- **格子标注**：在截图上叠加显示 slot 位置标注（红色圆点 + slot_id 标签）
- **标注开关**：复选框控制是否显示格子标注
- **截图保存**：提供"保存截图"按钮，将当前截图保存为 PNG 文件
- **Pillow 不可用**：若 Pillow 未安装，画面标签页显示提示信息 "需要安装 Pillow: pip install td-executor[ui]"

#### Scenario: 执行中自动刷新
- **WHEN** 执行器正在运行
- **THEN** 画面标签页每 2 秒自动刷新游戏窗口截图

#### Scenario: 格子标注
- **WHEN** 用户勾选"显示格子标注"复选框
- **THEN** 截图上叠加显示 slot 位置标注

#### Scenario: Pillow 不可用
- **WHEN** Pillow 未安装
- **THEN** 画面标签页显示安装提示，不崩溃

### Requirement: CLI gui 命令

系统 SHALL 在 CLI 中新增 `gui` 命令，启动可视化界面。

- `td-executor gui` 命令启动 GUI 主窗口
- tkinter 不可用时（如无显示环境），打印错误提示并退出
- 新增 `ui` 可选依赖组：`Pillow>=10.0.0`（用于截图处理和显示）

#### Scenario: 启动 GUI
- **WHEN** 用户执行 `td-executor gui`
- **THEN** 启动 GUI 主窗口

#### Scenario: 无显示环境
- **WHEN** 在无显示环境（如 SSH 终端）中执行 `td-executor gui`
- **THEN** 打印错误提示 "无法启动 GUI：未检测到显示环境"，退出码 1

### Requirement: 执行器与 GUI 的线程安全集成

系统 SHALL 确保执行器在子线程中运行，GUI 在主线程中运行，两者通过线程安全的方式通信。

- 执行器在子线程（daemon=True）中运行，不阻塞 GUI 主线程
- 使用 `queue.Queue` 传递执行事件（动作开始、动作完成、波次切换、执行完成等）
- GUI 主线程通过 `tkinter.after(100, poll_queue)` 每 100ms 轮询事件队列
- 事件类型定义：`ActionStartEvent`、`ActionCompleteEvent`、`WaveChangeEvent`、`ExecutionDoneEvent`
- 停止标志使用 `threading.Event`，执行器在每个动作前检查停止标志

#### Scenario: 动作完成事件
- **WHEN** 执行器完成一个动作
- **THEN** 将 ActionCompleteEvent 放入队列，GUI 轮询后更新监控面板

#### Scenario: 停止执行
- **WHEN** 用户点击停止按钮
- **THEN** 设置 threading.Event，执行器在下一个动作前检测到停止标志并退出

## MODIFIED Requirements

### Requirement: CLI 命令扩展

`td_executor.cli` SHALL 新增 `gui` 命令，调用 `td_executor.ui.app.launch()` 启动 GUI。

### Requirement: pyproject.toml 依赖扩展

`pyproject.toml` SHALL 新增 `ui` 可选依赖组，包含 `Pillow>=10.0.0`。
