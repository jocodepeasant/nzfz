# nzfz-executor · 逆战塔防自动化脚本执行器

基于 Python 3.10+ 的逆战塔防游戏自动化执行引擎，支持 JSON 脚本校验、GUI 可视化管理、游戏窗口连接与自动化执行。

> **版本**: 0.1.0 — 核心框架已搭好，部分模块为骨架待实现。

## 功能概览

| 状态 | 模块 | 说明 |
|------|------|------|
| ✅ | GUI（PySide6） | 游戏连接页签，窗口搜索 / 连接 / 断开 / 健康检测 |
| ✅ | CLI（typer） | `validate` / `run` / `gui` 三条命令 |
| ✅ | 脚本校验 | JSON Schema v1 校验 |
| ✅ | 深色主题 | Catppuccin Mocha 风格 QSS |
| 🔧 | 核心引擎 | 骨架就绪（engine / dispatcher / pipeline / scheduler） |
| 🔧 | 动作处理器 | 骨架就绪（放置 / 升级 / 拆除 / 拖拽 / 日志） |
| 🔧 | 条件判断 | 骨架就绪（条件处理器 + 求值器） |
| 🔧 | 重试策略 | 骨架就绪（策略定义 + 管理器） |
| 🔧 | 视觉识别 | 骨架就绪（模板匹配 / OCR） |
| 🔧 | 运行时能力 | 骨架就绪（窗口管理 / 截图 / 输入 / 叠加层） |

## 环境要求

- Python >= 3.10
- Windows（逆战游戏运行平台）

## 安装

```bash
# 基础安装（校验、CLI）
pip install -e executor/

# 带 GUI 支持
pip install -e "executor/[ui]"

# 完整开发环境
pip install -e "executor/[runtime,input,ocr,ui,dev]"
```

可选依赖组说明：

| 组名 | 内容 |
|------|------|
| `ui` | PySide6 ≥ 6.6、Pillow |
| `runtime` | numpy、opencv-python-headless、mss、loguru |
| `input` | pynput、pyautogui |
| `ocr` | paddleocr |
| `dev` | pytest、ruff |

## 启动方式

### 方式一：CLI 命令（推荐，pip install 后可用）

```bash
nzfz-executor gui                        # 启动 GUI
nzfz-executor validate <脚本路径>         # 校验脚本
nzfz-executor run <脚本路径>              # 执行脚本
nzfz-executor run <脚本路径> --dry-run    # 仅校验不执行
nzfz-executor run <脚本路径> --title 逆战 # 指定窗口标题关键字
```

### 方式二：直接运行

```bash
cd executor
python main.py
```

### 方式三：模块运行（开发调试）

```bash
python -m nzfz_executor gui
```

## CLI 命令详解

### `validate` — 校验脚本

校验塔防脚本 JSON 是否满足 Schema 定义。

```bash
nzfz-executor validate tower_defense_script.json
```

- 输入为空菜单时输出校验结果
- 校验通过显示绿色提示，失败列出所有错误项

### `run` — 执行脚本

加载并执行塔防自动化脚本。

```bash
nzfz-executor run tower_defense_script.json
nzfz-executor run tower_defense_script.json --dry-run
nzfz-executor run tower_defense_script.json --title "逆战"
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--dry-run` | 只加载与校验，不执行游戏操作 | `False` |
| `--title` | 游戏窗口标题关键字 | `逆战` |

> ⚠️ 当前 `run` 命令仅完成脚本加载和校验，游戏内执行逻辑尚未实现。

### `gui` — 启动 GUI

启动 PySide6 深色主题图形界面，首版包含「游戏连接」页签：

- 搜索游戏窗口（按进程名或窗口标题）
- 连接 / 断开窗口
- 实时状态显示（未连接 / 连接中 / 已连接 / 异常 / 超时）
- 健康检测（每秒轮询 + 断线自动重连）

```bash
nzfz-executor gui
```

## 项目结构

```
executor/
├── README.md
├── main.py                 # GUI 启动入口（直接运行）
├── pyproject.toml          # 包配置与依赖声明
├── assets/
│   └── style.qss           # 全局深色主题样式（Catppuccin Mocha）
└── tests/

nzfz_executor/              # Python 包
├── __init__.py             # 版本号 0.1.0
├── __main__.py             # python -m 入口
├── cli.py                  # CLI 命令行（validate / run / gui）
├── errors.py               # 统一异常体系（6 个异常类）
├── events.py               # 事件总线（on / emit / off）
├── context.py              # 执行上下文（ExecutionContext）
├── config.py               # 全局配置（ExecutorConfig）
├── lifecycle.py            # 生命周期管理（IDLE → RUNNING → PAUSED → STOPPED）
├── core/                   # 核心引擎
│   ├── engine.py           # 主引擎 ExecutorEngine
│   ├── dispatcher.py       # 动作分发器 ActionDispatcher
│   ├── pipeline.py         # 执行管线 ExecutionPipeline
│   ├── scheduler.py        # 波次调度器 WaveScheduler
│   └── window_manager.py   # 窗口管理器（Mock 接口）
├── actions/                # 动作处理器
│   ├── base.py             # 基类 ActionHandler + 注册表 ActionRegistry
│   ├── place.py            # 放置陷阱
│   ├── upgrade.py          # 升级陷阱
│   ├── remove.py           # 拆除陷阱
│   ├── pan.py              # 地图拖拽
│   └── log.py              # 日志输出
├── conditions/             # 条件判断
│   ├── base.py             # 基类 ConditionHandler + 注册表
│   └── evaluator.py        # 求值器 ConditionEvaluator
├── retry/                  # 重试策略
│   ├── policy.py           # RetryPolicy / OnFailPolicy
│   └── manager.py          # RetryManager
├── runtime/                # 运行时能力
│   ├── window.py           # WindowManager（窗口查找/聚焦）
│   ├── capture.py          # ScreenCapture（屏幕截图）
│   ├── input.py            # InputController（鼠标/键盘模拟）
│   └── overlay.py          # OverlayRenderer（窗口叠加层）
├── vision/                 # 视觉识别
│   ├── detector.py         # VisionDetector（模板匹配）
│   └── ocr.py              # OCRReader（文字识别）
├── script/                 # 脚本处理
│   ├── loader.py           # ScriptLoader（JSON 加载）
│   └── validator.py        # ScriptValidator（Schema 校验）
├── report/                 # 报告生成
│   └── builder.py          # ReportBuilder（RunReport）
└── ui/                     # GUI 界面
    ├── main_window.py      # 主窗口（QMainWindow + QTabWidget）
    └── tabs/
        └── game_connect.py # 游戏连接页签
```

## 开发

```bash
# 安装开发依赖
pip install -e "executor/[dev,ui]"

# 代码检查
ruff check nzfz_executor/

# 运行测试
pytest
```