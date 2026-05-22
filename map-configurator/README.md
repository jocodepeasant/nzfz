# 地图配置器（骨架）

Electron + Vite + React + TypeScript。开发时从本目录运行 `npm run dev`，主进程使用仓库根下 `schemas/tower_defense_script_v1.schema.json` 校验脚本。

## 产品需求与 MVP

可视化地图编辑、楼层、工程结构与验收用例见：

- [`docs/tower_defense_map_configurator_requirements_v2_draft.md`](../docs/tower_defense_map_configurator_requirements_v2_draft.md)
- P0 工程实现清单（对照）：[`docs/map_configurator_p0_implementation_guide.md`](../docs/map_configurator_p0_implementation_guide.md)

**单页工作台（当前）**

- **布局**：左侧地图画布 + 右侧可滚动 Inspector（分区折叠），无 Tab 切换。
- **地图联动**：槽位圆点实时显示；空白处点击添加、拖动移动；选中与右侧表格双向高亮；ROI 半透明矩形与表单联动。
- **多楼层**：`project.json` 的 `floors[]`；顶栏/Inspector 切换楼层；按楼层导入 `assets/floor_{id}.*`；槽位/区域带 `floor_id`；导出写入 `map.floors` / `map.default_floor_id`。
- **识别 ROI**：新建脚本 **无预置 ROI**；id 默认 `roi_1`、`roi_2`… 自增，可直接点「框选 ROI」；同 id 再次框选会更新矩形；也可 Inspector 微调数字。
- **高级 JSON**：Inspector「高级 JSON」为 CodeMirror 编辑器，**Ctrl+F**（macOS **Cmd+F**）查找与高亮。
- **底图 1:1**：`scale=1` 时按图片原始像素显示，超出画布区域滚动查看（滚轮缩放仍为仅会话查看）。
- **槽位**：须点地图工具 **「放置槽位」** 后再点击地图；工程默认显示半径 **0.5**、识别半边长 **1**、点击容差 **1**（px，可在 Inspector「楼层」区修改）。
- **应用陷阱库**：顶栏 **「陷阱库」** 进入**全页**陷阱管理（地图/Inspector 隐藏）；数据位于 `map-configurator/traps/` 与 `assets/verify_templates/`，**应用启动即加载**，与工程无关；增删改自动落盘；表单无选择键/升级键（导出时补默认值）。
- **底图标定**：地图工具 **「标定有效区域」** 拖拽绿框 → 写入 `map.calibration.content_rect`；槽位坐标相对该框。
- **仅查看的缩放**：滚轮以**鼠标位置**为中心缩放；**方向键**平移视野（Shift 加速）；选中槽位时方向键微调位置（Shift+方向键仍平移视野）；**右键/中键/空格+左键**拖拽平移；工具栏 ↑↓←→ 与「删除选中」；**Delete** 删除地图上选中的槽位/ROI，Inspector 选中区域/陷阱时 **Delete** 删除。
- **视图状态**：上述平移/缩放为会话状态（`sessionStorage`），**不写入** `export/script.json`。
- **区域说明**：Inspector 内说明 region 语义；选中区域可表单编辑 `enter_actions`（pan_map 序列）。

1. **工程**：顶栏选择目录；`project.json` / `assets` / `export`；Inspector「楼层」区保存工程元数据（不含陷阱库）。
2. **元数据 / 区域 / 槽位 / ROI / 波次**：右侧 Inspector；**陷阱**在顶栏「陷阱库」编辑（无需先选工程）。
3. **导出**：校验后写入 `export/script.json`（含多楼层字段与应用陷阱库）；支持另存为与打开外部 JSON。

使用步骤：`npm run dev` → 顶栏 **陷阱库**（全页）配置陷阱与识别图 → **选择工程目录** → **返回地图** → Inspector **导入底图** → 地图工具栏编辑 → **导出**。

旧版 9 Tab 界面已移除；单楼层工程会在打开时自动迁移为 `floors: [{ floor_id: "1", ... }]`。

**若按钮无反应**：须用 **`npm run dev`（Electron）** 启动；若只开了 Vite 浏览器页（无 Electron），`window.projectApi` 不存在。另请确认系统文件夹对话框未躲在其他窗口后面（已改为挂到当前 Electron 窗口）。

**导出前**：配置 `place_trap` 前请先至少有一个 **slot**，否则校验可能失败。

### 导出 `export/script.json` 与陷阱库

- **Schema**：仍为 `schemas/tower_defense_script_v1.schema.json`（`schema_version` 等顶层结构未变）。
- **`traps[]` 来源**：应用启动时从 `map-configurator/traps/*.json` 加载；导出时经 `buildScriptForExport` 写入工程 `export/script.json`，**不**从用户工程的 `project.json` 或工程内 `traps/` 读取。
- **陷阱项字段**：必填仍为 `trap_id`、`trap_name`、`select_key`、`upgrade_key`、`upgrade_hold_ms`、`cost`、`upgrade_cost`、`max_level`、`upgrade_mode`。编辑器表单不填键位时，导出 `select_key` / `upgrade_key` 均为 `"1"`。
- **`recognition_template`（可选）**：陷阱库中配置了识别图时，导出项增加该字段，值为相对 **map-configurator 根** 的路径（如 `assets/verify_templates/trap_trap_a.png`）。执行器加载脚本时需按部署方式解析该路径（与工程 `assets/` 无关）。

## 命令

- `npm run dev` — 开发调试
- `npm run build` — 构建主进程 / 预加载 / 渲染进程
- `npm run preview` — 预览生产构建
- `npm run pack` — `electron-builder --dir` 打目录包（需已 `build`）

## 故障排除（Windows）

若 `npm run dev` 报错 **`Error: Electron uninstall`**，多为 `node_modules/electron` 内缺少 `path.txt` / 二进制未下载。可在 **PowerShell** 中执行：

```powershell
cd map-configurator
.\scripts\bootstrap-electron.ps1
npm install
npm run dev
```

若 `npm install electron` 时出现 **`EBUSY` 无法重命名`**，请先关闭占用该目录的进程（本机杀毒、其他终端里的 `npm run dev` 等），再重试。
