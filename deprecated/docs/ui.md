# UI 模块 — 可视化界面

UI 模块提供基于 Tkinter 的图形界面，包含脚本管理、执行监控、画面预览和报告查看等功能。通过事件队列实现 GUI 线程与执行器线程的安全通信。

## 模块结构

```
ui/
├── __init__.py              # 模块导出（事件类）
├── app.py                   # 主窗口
├── events.py                # 事件定义
├── executor_bridge.py       # 执行器线程桥接
├── monitor_tab.py           # 监控标签页
├── preview_tab.py           # 画面预览标签页
├── report_tab.py            # 报告标签页
├── script_tab.py            # 脚本标签页
└── window_select_dialog.py  # 窗口选择对话框
```

---

## app.py — 主窗口

### 概述

`ExecutorApp` 是整个 GUI 的入口，继承 `tk.Tk`，管理标签页、状态栏和窗口连接。

### 核心类

#### `ExecutorApp(tk.Tk)`

```python
class ExecutorApp(tk.Tk):
    def __init__(self)
    def set_status(self, status: str) -> None
    def set_window_info(self, info: str) -> None
    def connect_window(self, title_keyword: str) -> bool
    def connect_window_by_hwnd(self, hwnd: int) -> bool
    def disconnect_window(self) -> None
    def start_polling(self) -> None
```

**界面布局：**
- **标签页区域**（`ttk.Notebook`）：监控、脚本、报告、画面
- **状态栏**（底部）：状态标签 | 窗口信息 | 时钟

**标签页：**
| 标签 | 类 | 说明 |
|------|---|------|
| 监控 | `MonitorTab` | 实时执行状态 |
| 脚本 | `ScriptTab` | 脚本加载与运行控制 |
| 报告 | `ReportTab` | 历史报告查看 |
| 画面 | `PreviewTab` | 游戏画面预览 |

**窗口连接流程：**
1. 调用 `find_game_window` 查找游戏窗口
2. 获取 `WindowRect` 信息
3. 创建 `WindowOverlay` 覆盖层
4. 通知 `PreviewTab` 更新窗口信息

**事件轮询：**
- 每 100ms 从 `ExecutorBridge` 的事件队列取事件
- 根据事件类型分发到对应标签页

#### `launch()`

启动 GUI 主循环。若检测不到显示环境则退出。

---

## events.py — 事件定义

### 概述

定义 GUI 与执行器之间的事件类型，所有事件均为 `dataclass`。

### 事件类型

#### `ActionStartEvent`

动作开始执行时触发。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `action_index` | `int` | 动作序号 |
| `action_type` | `str` | 动作类型 |
| `action_name` | `str` | 动作名称 |
| `wave` | `int` | 所属波次 |

#### `ActionCompleteEvent`

动作执行完成时触发。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `action_index` | `int` | 动作序号 |
| `action_type` | `str` | 动作类型 |
| `action_name` | `str` | 动作名称 |
| `wave` | `int` | 所属波次 |
| `success` | `bool` | 是否成功 |
| `skipped` | `bool` | 是否跳过 |
| `retry_count` | `int` | 重试次数 |
| `error_message` | `str \| None` | 错误信息 |
| `duration_ms` | `float` | 耗时（毫秒） |

#### `WaveChangeEvent`

波次切换时触发。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `wave` | `int` | 当前波次 |
| `total_waves` | `int` | 总波次数 |
| `wave_action_count` | `int` | 当前波次动作数 |

#### `ExecutionDoneEvent`

脚本执行完成时触发。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `result` | `str` | 结果（`completed` / `stopped` / `error`） |
| `total_actions` | `int` | 总动作数 |
| `success_count` | `int` | 成功数 |
| `fail_count` | `int` | 失败数 |
| `skip_count` | `int` | 跳过数 |
| `duration_seconds` | `float` | 运行时长 |

---

## executor_bridge.py — 执行器线程桥接

### 概述

`ExecutorBridge` 是 GUI 线程与执行器线程之间的桥梁，使用 `queue.Queue` 实现线程安全的事件传递，使用 `threading.Event` 实现停止控制。

### 核心类

#### `ExecutorBridge`

```python
class ExecutorBridge:
    def __init__(self)
    @property
    def running(self) -> bool
    @property
    def stop_requested(self) -> bool
    def get_event(self, timeout=0.0) -> Any | None
    def request_stop(self) -> None
    def set_overlay(self, overlay) -> None
    def reset(self) -> None
    def start_execution(self, script_data, title_keyword, dry_run, window_rect, debug, on_done) -> bool
```

**`start_execution` 参数：**

| 参数 | 类型 | 说明 |
|-----|------|------|
| `script_data` | `dict` | 脚本数据 |
| `title_keyword` | `str` | 窗口标题关键字 |
| `dry_run` | `bool` | 是否试运行 |
| `window_rect` | `WindowRect \| None` | 窗口矩形 |
| `debug` | `bool` | 调试模式 |
| `on_done` | `Callable \| None` | 完成回调 |

**执行流程：**
1. 在守护线程中执行脚本
2. 查找/验证游戏窗口
3. 初始化 `ScreenCapture`
4. 创建 `ActionExecutor` 和执行上下文
5. 按波次遍历动作，发送事件到队列
6. 支持试运行模式（跳过实际执行）
7. 执行完成后生成报告并保存到 `reports/` 目录

**停止机制：**
- 调用 `request_stop()` 设置停止标志
- 执行线程在每个动作前检查停止标志
- 停止后报告结果标记为 `stopped`

---

## monitor_tab.py — 监控标签页

### 概述

实时显示脚本执行状态，包括波次进度、动作列表和运行统计。

### 核心类

#### `MonitorTab(ttk.Frame)`

**界面布局：**
- **波次进度**（顶部）：波次标签 + 进度条
- **动作列表**（左侧）：Treeview，显示序号、类型、名称、状态、重试次数、耗时
- **统计面板**（右侧）：总动作数、成功数、失败数、跳过数、运行时长

**状态颜色：**
| 状态 | 颜色 | 显示文本 |
|------|------|---------|
| 执行中 | 蓝色 | 执行中 |
| 成功 | 绿色 | ✓ 成功 |
| 失败 | 红色 | ✗ 失败 |
| 跳过 | 金色 | ⊘ 跳过 |
| 等待 | 灰色 | — |

**事件处理：**
- `on_action_start` — 插入新行，标记为"执行中"
- `on_action_complete` — 更新行状态和统计数据
- `on_wave_change` — 更新波次进度
- `on_execution_done` — 更新最终统计

---

## preview_tab.py — 画面预览标签页

### 概述

实时预览游戏画面，支持格子标注叠加和截图保存。依赖 Pillow 库。

### 核心类

#### `PreviewTab(ttk.Frame)`

**界面布局：**
- **控制栏**（顶部）：刷新截图、保存截图、显示格子标注复选框
- **画布**（中央）：显示游戏画面

**功能：**
- **自动刷新**：执行期间每 2 秒自动截图刷新
- **格子标注**：在截图上叠加红色圆圈和 slot_id 标签
- **截图保存**：保存当前画面为 PNG 文件
- **自适应缩放**：根据画布尺寸等比缩放显示

**依赖：** Pillow（`pip install td-executor[ui]`）

---

## report_tab.py — 报告标签页

### 概述

查看历史执行报告，包括报告列表、统计摘要和动作日志详情。

### 核心类

#### `ReportTab(ttk.Frame)`

**界面布局：**
- **报告列表**（左侧）：Treeview，显示时间、脚本名、结果、时长
- **统计摘要**（右上）：总动作数、成功数、失败数、运行时长
- **动作日志**（右下）：Treeview，显示波次、类型、名称、状态、重试次数、错误信息
- **导出按钮**（右下）：导出选中报告为 JSON 文件

**功能：**
- `refresh_reports()` — 从 `reports/` 目录加载所有 `report_*.json` 文件
- 点击报告列表项显示详细统计和动作日志
- 支持导出报告为 JSON 文件

---

## script_tab.py — 脚本标签页

### 概述

脚本管理标签页，负责脚本加载、校验、窗口连接和执行控制。

### 核心类

#### `ScriptTab(ttk.Frame)`

**界面布局：**
- **脚本文件**（顶部）：路径输入框 + 浏览按钮 + 校验按钮
- **脚本预览**（中部）：显示地图、波次、操作数、陷阱列表摘要
- **运行参数**（中下）：窗口标题关键字 + 连接窗口按钮 + 试运行/调试复选框
- **控制按钮**（底部）：启动（绿色）、停止（红色）、重置（灰色）

**操作流程：**
1. 浏览选择脚本 JSON 文件
2. 点击"校验"验证脚本合法性
3. 点击"连接窗口"选择游戏窗口
4. 点击"启动"开始执行（自动切换到监控标签页）
5. 执行完成后恢复按钮状态

**窗口连接：**
- 点击"连接窗口"打开 `WindowSelectDialog`
- 选择窗口后调用 `app.connect_window_by_hwnd`
- 连接成功后按钮变为"断开连接"

---

## window_select_dialog.py — 窗口选择对话框

### 概述

模态对话框，用于从匹配的窗口列表中选择目标游戏窗口。

### 核心类

#### `WindowSelectDialog(tk.Toplevel)`

**界面布局：**
- **窗口列表**：Treeview，显示窗口标题和句柄
- **按钮**：连接、取消

**交互：**
- 选中列表项后"连接"按钮可用
- 双击列表项等同于点击"连接"
- 点击"连接"后设置 `selected_hwnd` 并关闭对话框
- 点击"取消"后 `selected_hwnd` 为 `None`

**定位：** 居中于父窗口
