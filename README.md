# 逆战塔防自动化通关系统

《逆战：未来》塔防模式自动化通关工具，包含 **地图配置器** 与 **自动化执行器** 两个子系统，通过共享 JSON Schema 解耦、可并行开发。

## 系统架构

```text
┌─────────────────┐    script.json    ┌─────────────────┐
│   地图配置器     │ ───────────────→ │  自动化执行器    │ ──→ 游戏
│  Electron/React  │  (JSON Schema v1) │  Python/PySide6  │
└─────────────────┘                   └─────────────────┘
        ↑                                     ↑
        └─────── schemas/ (共享协议) ──────────┘
```

- **地图配置器**：可视化编辑地图、陷阱、区域、槽位、波次，导出合规脚本 JSON
- **自动化执行器**：读取脚本 JSON，连接游戏窗口，按波次自动执行放置/升级/拆除等操作
- **共享 Schema**：[`schemas/tower_defense_script_v1.schema.json`](schemas/tower_defense_script_v1.schema.json) 定义脚本协议，两端共同遵守

## 目录结构

| 路径 | 说明 |
|------|------|
| [`executor/`](executor/) | 执行器包配置（pyproject.toml）与 GUI 启动入口 |
| [`nzfz_executor/`](nzfz_executor/) | 执行器 Python 包源码（核心引擎 / 动作处理器 / GUI 等） |
| [`map-configurator/`](map-configurator/) | 地图配置器（Electron + Vite + React + TypeScript） |
| [`schemas/`](schemas/) | 共享 JSON Schema v1 与示例脚本 |
| [`docs/`](docs/) | 需求文档与实现指南 |
| [`deprecated/`](deprecated/) | 已废弃的旧模块文档 |

## 地图配置器

> 技术栈：Electron · Vite · React · TypeScript

可视化地图编辑工具，支持底图导入、槽位放置、ROI 框选、多楼层管理、陷阱库配置，导出合规 `script.json`。

```bash
cd map-configurator
npm install
npm run dev
```

详细功能与使用说明见 → [map-configurator/README.md](map-configurator/README.md)

## 自动化执行器

> 技术栈：Python 3.10+ · PySide6 · typer · rich

逆战塔防自动化执行引擎，提供 GUI 可视化管理与 CLI 命令行两种使用方式。

**功能概览：**

| 状态 | 模块 | 说明 |
|------|------|------|
| ✅ | GUI（PySide6） | 游戏连接页签：窗口搜索 / 连接 / 断开 / 健康检测 |
| ✅ | CLI（typer） | `validate` / `run` / `gui` 三条命令 |
| ✅ | 深色主题 | Catppuccin Mocha 风格 QSS |
| 🔧 | 核心引擎 | 骨架就绪（engine / dispatcher / pipeline / scheduler） |
| 🔧 | 动作处理器 | 骨架就绪（放置 / 升级 / 拆除 / 拖拽 / 日志） |
| 🔧 | 视觉识别 | 骨架就绪（模板匹配 / OCR） |
| 🔧 | 运行时能力 | 骨架就绪（窗口管理 / 截图 / 输入 / 叠加层） |

**快速开始：**

```bash
# 安装（带 GUI 支持）
pip install -e "executor/[ui]"

# 启动 GUI
nzfz-executor gui

# 校验脚本
nzfz-executor validate schemas/examples/space_station_normal_baseline_v1.json

# 执行脚本（dry-run）
nzfz-executor run schemas/examples/space_station_normal_baseline_v1.json --dry-run
```

详细安装、CLI 详解与项目结构见 → [executor/README.md](executor/README.md)

## 脚本协议

脚本 JSON 遵循 [`schemas/tower_defense_script_v1.schema.json`](schemas/tower_defense_script_v1.schema.json)，包含地图定义、陷阱配置、区域/槽位、波次动作等字段。

示例脚本：[`schemas/examples/space_station_normal_baseline_v1.json`](schemas/examples/space_station_normal_baseline_v1.json)

## 设计文档

- [`tower_defense_automation_design_v1.md`](tower_defense_automation_design_v1.md) — 系统需求与架构设计 V1.0
- [`docs/tower_defense_map_configurator_requirements_v2_draft.md`](docs/tower_defense_map_configurator_requirements_v2_draft.md) — 地图配置器 V2 需求草案
- [`docs/map_configurator_p0_implementation_guide.md`](docs/map_configurator_p0_implementation_guide.md) — 地图配置器 P0 实现指南