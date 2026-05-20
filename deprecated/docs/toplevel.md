# 顶层模块

顶层模块包含命令行入口、对局状态管理和 BOSS 预留逻辑。

## 文件结构

```
td_executor/
├── __init__.py         # 包初始化
├── __main__.py         # python -m 入口
├── cli.py              # 命令行接口
├── state.py            # 对局状态管理
└── boss_reserved.py    # BOSS 预留模块导出
```

---

## __init__.py — 包初始化

```python
"""Tower defense automation executor package (V1 skeleton)."""
__version__ = "0.0.1"
```

当前仅定义版本号，后续将导出核心公共 API。

---

## __main__.py — 模块入口

支持 `python -m td_executor` 方式运行，委托给 `cli.app()`。

```python
from td_executor.cli import app

if __name__ == "__main__":
    app()
```

---

## cli.py — 命令行接口

### 概述

基于 Typer 框架的命令行工具，提供脚本校验、运行和 GUI 启动三个子命令。

### 命令

#### `td-executor validate <path>`

校验脚本 JSON 文件是否符合 Schema。

**参数：**
- `path` — 脚本文件路径

**输出：**
- 校验通过：绿色提示
- 校验失败：表格显示错误路径和说明，退出码 1

#### `td-executor run <path>`

加载并运行脚本。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `path` | `Path` | — | 脚本文件路径 |
| `--dry-run` | `bool` | `False` | 只加载与校验，不操作游戏 |
| `--title` | `str` | `"逆战"` | 游戏窗口标题关键字 |

**流程：**
1. 加载脚本文件
2. 校验脚本数据
3. 若 `--dry-run`，输出提示后退出
4. 查找游戏窗口
5. 输出窗口信息（游戏内执行尚未完全实现）

#### `td-executor gui`

启动可视化 GUI 界面。委托给 `td_executor.ui.app.launch()`。

### 依赖

| 库 | 用途 |
|---|------|
| `typer` | 命令行框架 |
| `rich` | 终端美化输出 |

---

## state.py — 对局状态管理

### 概述

跟踪当前对局的运行状态，包括波次、窗口信息和焦点状态。当前为占位实现，后续将扩展资源、血量等字段。

### 核心类

#### `GameState`

```python
class GameState:
    wave: int | None = None
    window_handle: int | None = None
    window_rect: WindowRect | None = None
    is_focused: bool = False

    def update_window(self, rect: WindowRect, focused: bool = True) -> None
    def clear_window(self) -> None
```

**字段说明：**

| 字段 | 类型 | 说明 |
|-----|------|------|
| `wave` | `int \| None` | 当前波次 |
| `window_handle` | `int \| None` | 游戏窗口句柄 |
| `window_rect` | `WindowRect \| None` | 窗口矩形信息 |
| `is_focused` | `bool` | 窗口是否获得焦点 |

**方法：**
- `update_window(rect, focused=True)` — 更新窗口信息
- `clear_window()` — 清除窗口信息

---

## boss_reserved.py — BOSS 预留模块导出

### 概述

与脚本 `boss_reserved` 字段对应的模块导出，当前仅转发 `engine.boss.handle_boss_reserved`。

```python
from td_executor.engine.boss import handle_boss_reserved

__all__ = ["handle_boss_reserved"]
```
