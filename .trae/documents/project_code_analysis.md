# 项目代码深入理解分析

## 1. 项目概览

**项目名称**：逆战：未来 · 塔防自动化通关测试系统

**核心目标**：为《逆战：未来》塔防模式构建一套自动化通关系统，包含两个解耦的子系统：
- **地图配置器**（Electron + React + TypeScript）：可视化编辑地图、陷阱、槽位、波次，导出脚本 JSON
- **自动化执行器**（Python）：读取脚本 JSON，在游戏窗口内执行自动化操作

**通信协议**：两者仅通过 `tower_defense_script_v1.schema.json` 定义的 JSON 协议通信，可完全并行开发。

---

## 2. 仓库目录结构

```
/workspace/
├── .trae/specs/                    # 各功能模块的 spec/checklist/tasks
├── deprecated/docs/                # 旧版设计文档（已废弃）
├── docs/                           # 地图配置器 V2 需求草案
├── map-configurator/               # 地图配置器（Electron 应用）
│   ├── src/main/                   # Electron 主进程
│   │   ├── index.ts                # 主进程入口 + IPC 注册
│   │   ├── app-paths.ts            # 应用路径工具
│   │   ├── project-fs.ts           # 工程文件系统操作
│   │   └── trap-fs.ts              # 陷阱库文件系统操作
│   ├── src/preload/                # Electron preload 脚本
│   ├── src/renderer/src/           # React 渲染进程
│   │   ├── App.tsx                 # 根组件
│   │   ├── EditorWorkspace.tsx     # 主工作台（状态管理中心）
│   │   ├── MapCanvas.tsx           # 地图画布（槽位放置/ROI框选/缩放平移）
│   │   ├── InspectorPanel.tsx      # 右侧检查面板（楼层/元数据/区域/槽位/ROI/波次/导出）
│   │   ├── TrapLibraryPanel.tsx    # 陷阱库管理页面
│   │   ├── WavesEditor.tsx         # 波次编辑器
│   │   ├── JsonEditor.tsx          # JSON 编辑器
│   │   └── script/                 # 脚本相关工具模块
│   │       ├── types.ts            # TypeScript 类型定义
│   │       ├── defaultScript.ts    # 默认脚本创建/序列化/反序列化
│   │       ├── mapCoords.ts        # 坐标换算（contentRect/比例坐标）
│   │       ├── mapTools.ts         # 地图工具模式（放置槽位/框选ROI/标定区域）
│   │       ├── mapViewport.ts      # 视口缩放平移
│   │       ├── projectUtils.ts     # 工程文件工具（楼层/导出构建）
│   │       ├── roiUtils.ts         # ROI 管理工具
│   │       └── trapUtils.ts        # 陷阱库工具
│   ├── traps/                      # 陷阱定义 JSON 文件
│   └── package.json                # Electron + React + Ajv + CodeMirror
├── nzfz_executor/                  # 自动化执行器（Python，新架构）
│   ├── core/
│   │   ├── __init__.py             # 导出 ExecutorEngine/ActionDispatcher/ExecutionPipeline/WaveScheduler
│   │   ├── models.py               # 窗口连接数据模型
│   │   └── window_manager.py       # 窗口管理器（搜索/连接/断开/健康检测）
│   └── ui/tabs/
│       └── game_connect.py         # 游戏连接 UI 页签（PySide6）
├── schemas/                        # JSON Schema 与示例脚本
│   ├── tower_defense_script_v1.schema.json
│   └── examples/space_station_normal_baseline_v1.json
├── spec/                           # 需求与设计文档
│   ├── P0-01andP0-02详细设计文档.md
│   ├── 需求与架构设计 V1.0.md
│   └── 需求拆分文档 v1.0.md
└── README.md
```

---

## 3. 核心架构分析

### 3.1 双子系统解耦架构

```
地图配置器 (Electron/TS)  ←——JSON 协议——→  自动化执行器 (Python)
      ↓                                          ↓
  可视化编辑 + 导出 JSON                    加载 JSON + 游戏自动化
```

**设计原则**：
- 配置与执行完全解耦
- 地图适配配置化（新地图通过配置适配，不改代码）
- 坐标比例化（`region_screen_ratio` 模式，适配不同分辨率）
- 动作原子化（放置/升级/拆除/等待/拖拽均抽象为动作）
- 条件驱动 + 可重试 + 可扩展

### 3.2 JSON 脚本协议（核心桥梁）

脚本 JSON 是两个子系统的唯一通信协议，顶层结构：

| 字段 | 说明 |
|------|------|
| `schema_version` | 协议版本 `1.0.x` |
| `script_id` / `script_name` | 脚本标识 |
| `map` | 地图信息（分辨率/坐标模式/初始视野/楼层/标定） |
| `runtime` | 运行参数（超时/重试/等待时间） |
| `recognition` | 识别区域配置（ROI + 多帧投票） |
| `traps` | 陷阱配置（热键/花费/升级参数） |
| `regions` | 地图区域配置（enter_actions 拖拽动作） |
| `slots` | 陷阱格子配置（位置/精度/校验区域） |
| `waves` | 波次动作配置（触发条件/动作链） |
| `boss_reserved` | BOSS 预留 |
| `metadata` | 元信息 |

**关键设计**：
- 坐标使用 `region_screen_ratio`（屏幕比例），`x_ratio`/`y_ratio` 为 0~1 的比例值
- `content_rect` 定义参考图上的有效地图区域，槽位坐标相对于此区域
- 支持多楼层（`floors`），每个 slot/region 可绑定 `floor_id`
- 动作类型：`pan_to_region` / `place_trap` / `upgrade_trap` / `remove_trap` / `log`
- 每个动作支持 `conditions`（条件判断）、`retry`（重试）、`on_fail`（失败策略）

---

## 4. 地图配置器（map-configurator）深入分析

### 4.1 技术栈

| 层级 | 技术 |
|------|------|
| 桌面框架 | Electron 33 + electron-vite 2 |
| UI 框架 | React 18 + TypeScript 5 |
| JSON 校验 | Ajv 8 (JSON Schema Draft 2020-12) |
| JSON 编辑 | @uiw/react-codemirror + @codemirror/lang-json |
| 构建 | Vite 5 + electron-builder |

### 4.2 主进程（Main Process）

[main/index.ts](file:///workspace/map-configurator/src/main/index.ts) 负责：
- 创建 BrowserWindow（1280×900，contextIsolation + sandbox:false）
- 注册 IPC handlers：
  - `validate-script`：Ajv 校验脚本 JSON
  - `open-script-file` / `save-script-file`：文件对话框
  - `project-select-dir` / `project-ensure-dirs` / `project-read-json` / `project-write-json`：工程目录管理
  - `project-read-export-script` / `project-write-export-script`：导出脚本读写
  - `project-import-floor-image` / `project-read-file-base64` / `project-file-exists`：图片资源管理
  - `trap-list-definitions` / `trap-sync-definitions` / `trap-import-recognition-image` / `trap-read-file-base64` / `trap-file-exists`：陷阱库管理

[main/project-fs.ts](file:///workspace/map-configurator/src/main/project-fs.ts) 提供：
- `resolveSafe()`：路径安全检查，防止路径穿越
- `ensureProjectDirs()`：创建 `assets/` 和 `export/` 目录
- `readProjectJson()` / `writeProjectJson()`：读写 `project.json`
- `readExportScript()` / `writeExportScript()`：读写 `export/script.json`
- `importFloorImage()`：导入楼层底图到 `assets/floor_{id}.{ext}`
- `readFileBase64()` / `fileExists()`：文件读取

[main/trap-fs.ts](file:///workspace/map-configurator/src/main/trap-fs.ts) 提供：
- 陷阱库 CRUD：`listTrapDefinitions()` / `writeTrapDefinition()` / `deleteTrapDefinition()` / `syncTrapDefinitions()`
- 识别图导入：`importTrapRecognitionImage()`
- 陷阱文件存储在 `map-configurator/traps/{trap_id}.json`

### 4.3 渲染进程（Renderer Process）

#### EditorWorkspace（状态管理中心）

[EditorWorkspace.tsx](file:///workspace/map-configurator/src/renderer/src/EditorWorkspace.tsx) 是整个配置器的核心，管理所有状态：

- `projectRoot`：工程根目录
- `projectFile: ProjectFileV1`：工程文件（楼层/陷阱库/槽位默认值）
- `script: TowerDefenseScript`：脚本数据（与 JSON 协议对齐）
- `floorDataUrl`：当前楼层底图的 data URL
- `rawJson` / `jsonError`：JSON 编辑器内容
- `selection: EditorSelection`：当前选中项（slot/roi/region/trap）
- `mapTool: MapToolMode`：当前地图工具模式
- `mapViewport: MapViewport`：地图视口（缩放/平移）
- `workspaceView`：工作区视图（map / trapLibrary）

**关键数据流**：
1. `setScriptAndSync`：更新脚本并同步 JSON 文本
2. `openOrInitProject`：打开工程 → 读取 project.json + export/script.json + 陷阱库
3. `buildScriptForExport`：构建导出脚本（合并 script + projectFile 元数据）
4. 陷阱库双向同步：UI 修改 → `trapApi.syncTrapDefinitions` → 磁盘 + `syncScriptTraps` → script

#### MapCanvas（地图画布）

[MapCanvas.tsx](file:///workspace/map-configurator/src/renderer/src/MapCanvas.tsx) 提供：
- 楼层底图显示 + 缩放平移（滚轮缩放/空格+拖拽平移/方向键平移）
- 槽位标记（颜色按陷阱类型区分，可拖拽移动）
- ROI 框选（可视化识别区域）
- contentRect 标定（有效地图区域）
- 工具模式：idle / placeSlot / drawRoi / calibrateContentRect

#### InspectorPanel（检查面板）

[InspectorPanel.tsx](file:///workspace/map-configurator/src/renderer/src/InspectorPanel.tsx) 包含：
- 楼层管理（切换/添加/导入底图/contentRect 编辑）
- 元数据编辑（script_id/map_id/difficulty 等）
- 区域管理（添加/删除/enter_actions 编辑）
- 槽位表格（slot_id/region/trap 选择/精度参数）
- ROI 管理（id/显示名/坐标/框选触发）
- 波次编辑（WavesEditor 组件）
- 导出操作（校验/写入/另存为/打开外部 JSON）
- 高级 JSON 编辑器

#### TrapLibraryPanel（陷阱库）

[TrapLibraryPanel.tsx](file:///workspace/map-configurator/src/renderer/src/TrapLibraryPanel.tsx) 提供：
- 应用级陷阱库管理（独立于工程，存储在 `map-configurator/traps/`）
- 识别图缩略图显示和导入
- 陷阱参数编辑（花费/升级/等级/模式）

### 4.4 坐标系统

**核心概念**：
- `RatioRect` / `RatioPoint`：0~1 比例坐标
- `contentRect`：参考图上的有效地图区域（槽位坐标相对于此）
- `imageNorm`：参考图全图比例坐标（0~1）
- `contentNorm`：contentRect 内的比例坐标（0~1）

**坐标转换**：
- `contentNormToImageNorm`：content 坐标 → image 坐标
- `imageNormToContentNorm`：image 坐标 → content 坐标
- `applySlotPosition`：根据 content 坐标计算 slot 的 position + verify.check_area

---

## 5. 自动化执行器深入分析

### 5.1 两套执行器架构

项目中存在**两套**执行器代码：

1. **nzfz_executor**（当前分支 `implement/p0-01-p0-02-window-connect-models-and-manager`）：
   - 新架构，使用 PySide6 GUI
   - 目前仅实现了窗口连接模块（P0-01/P0-02）
   - 核心模块声明了 `ExecutorEngine` / `ActionDispatcher` / `ExecutionPipeline` / `WaveScheduler`，但代码文件尚未创建

2. **automation-executor**（旧架构，代码不在当前工作区）：
   - 根据并行开发任务文档，已完成 T01~T12
   - 使用 tkinter GUI
   - 完整实现了屏幕采集/OCR/模板匹配/条件引擎/动作执行/重试/日志等

### 5.2 nzfz_executor 当前实现

#### core/models.py（窗口连接数据模型）

[models.py](file:///workspace/nzfz_executor/core/models.py) 定义：
- `WindowRect`：窗口矩形（left/top/right/bottom + width/height 属性）
- `WindowInfo`：搜索结果窗口信息（hwnd/title/process_name/pid/match_score）
- `ConnectedWindow`：已连接窗口上下文（hwnd/title/process_name/pid/window_rect/client_rect/dpi_scale）
- `HealthStatus`：健康状态枚举（HEALTHY/NOT_CONNECTED/HANDLE_INVALID/PROCESS_DEAD/WINDOW_HIDDEN/WINDOW_MINIMIZED/WINDOW_SIZE_INVALID）
- `ControlMode`：控制模式枚举（FOREGROUND/BACKGROUND/HYBRID）
- `ConnectOptions`：连接选项（activate_on_connect/restore_if_minimized/control_mode）
- `ConnectResult`：连接结果（success/window/error_message/activated + ok()/fail() 工厂方法）
- `HealthCheckResult`：健康检测结果（status/message/window + is_healthy/is_connected 属性）

#### core/window_manager.py（窗口管理器）

[window_manager.py](file:///workspace/nzfz_executor/core/window_manager.py) 提供：
- `search_windows(keyword)`：搜索匹配窗口（P0-02 阶段仅保留接口，返回空列表）
- `connect_window(window, options)`：连接指定窗口（P0-02 阶段仅保留接口，返回"尚未实现"）
- `disconnect_window()`：断开连接（清理内部状态，不影响游戏窗口）
- `check_health()`：健康检测（P0-02 阶段已连接返回 HEALTHY）
- `is_supported()` / `get_unsupported_reason()`：环境检查（仅 Windows + pywin32 + psutil）
- `_ensure_supported()`：实时检查运行环境

**重要**：`search_windows` 和 `connect_window` 的真实 Windows API 实现尚未完成，当前为桩代码。

#### ui/tabs/game_connect.py（游戏连接 UI）

[game_connect.py](file:///workspace/nzfz_executor/ui/tabs/game_connect.py) 使用 PySide6 实现：
- `ConnectState`：连接状态枚举（DISCONNECTED/CONNECTING/CONNECTED/ABNORMAL/TIMEOUT）
- `ConnectWorker(QThread)`：后台连接工作线程
- `GameConnectTab(QWidget)`：完整 UI 页签
  - 搜索区：关键词输入 + 搜索按钮 + 结果表格
  - 操作区：连接按钮 + 断开连接按钮
  - 状态区：指示灯 + 状态文字 + 窗口信息
  - 截图占位区（未实现）
  - 健康检测定时器（1 秒间隔）
  - 连接超时定时器（5 秒）
  - 状态联动：按钮启用/禁用根据连接状态自动切换

#### core/__init__.py（核心模块声明）

```python
from nzfz_executor.core.engine import ExecutorEngine
from nzfz_executor.core.dispatcher import ActionDispatcher
from nzfz_executor.core.pipeline import ExecutionPipeline
from nzfz_executor.core.scheduler import WaveScheduler
```

这四个模块（engine/dispatcher/pipeline/scheduler）已被声明但**尚未创建**，是后续开发的核心。

---

## 6. 开发进度与当前状态

### 6.1 当前分支

`implement/p0-01-p0-02-window-connect-models-and-manager`

### 6.2 P0 需求完成情况

| 编号 | 需求 | 状态 |
|------|------|------|
| P0-001 | 项目目录和启动入口 | ✅ |
| P0-002 | 共享 Schema v1 初版 | ✅ |
| P0-003 | 示例脚本 JSON | ✅ |
| P0-004 | 执行器主窗口 | ✅ (PySide6 框架) |
| P0-005 | 游戏窗口搜索 | ⚠️ 接口已定义，实现为桩代码 |
| P0-006 | 游戏窗口连接 | ⚠️ 接口已定义，实现为桩代码 |
| P0-007 | 断开连接 | ✅ |
| P0-008 | 健康检测 | ⚠️ 基础实现，真实检测逻辑待 P1 |
| P0-009 | 脚本加载 | ❌ |
| P0-010 | Schema 校验 | ❌ |
| P0-011~P0-018 | 动作模型/执行引擎/配置器 | ❌ |

### 6.3 并行开发任务进度（automation-executor 旧架构）

| 任务 | 状态 |
|------|------|
| T01-屏幕采集 | ✅ 已完成 |
| T02-单局日志 | ✅ 已完成 |
| T03-重试框架 | ✅ 已完成 |
| T04-OCR识别 | ✅ 已完成 |
| T05-模板匹配 | ✅ 已完成 |
| T06-条件引擎 | ✅ 已完成 |
| T07-按键动作基础 | ✅ 已完成 |
| T08-地图导航 | ✅ 已完成 |
| T09-格子定位 | ✅ 已完成 |
| T10-动作执行完整流程 | ✅ 已完成 |
| T11-重试集成 | ✅ 已完成 |
| T12-日志集成 | ✅ 已完成 |
| T13-批量执行 | ❌ 未完成 |

### 6.4 .trae/specs 中的功能模块

已完成的 spec 目录（含 checklist/tasks）：
- add-background-execution / add-execution-overlay / add-executor-gui
- fix-overlay-and-background-execution / fix-script-preview-traps / fix-window-connect-ux
- implement-action-execution / implement-condition-engine / implement-game-window-manager
- implement-key-action-basics / implement-map-navigator / implement-ocr-recognition
- implement-retry-framework / implement-run-report / implement-screen-capture
- implement-slot-positioning / implement-vision-detector

---

## 7. 关键技术决策与设计模式

### 7.1 地图配置器

1. **单页工作台模式**：EditorWorkspace 作为唯一状态管理中心，通过 props 向下传递
2. **双向 JSON 同步**：script 对象变更 → 自动序列化为 rawJson；rawJson 编辑 → 反序列化回 script
3. **工程文件 vs 脚本 JSON 分离**：`project.json` 存储工程元数据（楼层/视口/陷阱库），`export/script.json` 存储协议脚本
4. **陷阱库应用级共享**：陷阱定义存储在 `map-configurator/traps/` 目录，跨工程共享
5. **坐标系统**：contentRect 标定有效区域 → 槽位坐标相对于 contentRect → 导出时转换为全图比例

### 7.2 自动化执行器

1. **Core/UI 分层**：`core/` 纯逻辑层，`ui/` 仅负责展示和事件转发
2. **QThread 异步连接**：窗口连接在后台线程执行，避免阻塞 UI
3. **健康检测定时器**：1 秒间隔周期检测窗口状态，自动切换 CONNECTED/ABNORMAL
4. **平台兼容性**：`_ensure_supported()` 实时检查 Windows 环境，非 Windows 优雅降级
5. **ControlMode 预留**：FOREGROUND/BACKGROUND/HYBRID 三种控制模式，当前仅实现 FOREGROUND

---

## 8. 待完成的关键工作

### 8.1 nzfz_executor（新架构）

1. **窗口搜索/连接的真实实现**：`search_windows` 和 `connect_window` 目前为桩代码，需要调用 win32gui/psutil 实现
2. **核心引擎模块**：`engine.py` / `dispatcher.py` / `pipeline.py` / `scheduler.py` 已声明但未创建
3. **脚本加载与校验**：P0-009 / P0-010
4. **动作模型与执行**：P0-011 ~ P0-016
5. **前台输入通道**：P0-015

### 8.2 地图配置器

1. **波次编辑器增强**：当前仅支持 log/pan_to_region/place_trap 三种动作类型，缺少 upgrade_trap/remove_trap
2. **引用完整性校验**：slot_id/trap_id 引用检查
3. **配置器导入脚本**：打开已有脚本并还原编辑状态

### 8.3 跨系统

1. **automation-executor 旧架构代码不在当前工作区**：需要确认是否已迁移或合并
2. **T13 批量执行**：最后一个未完成的并行开发任务
