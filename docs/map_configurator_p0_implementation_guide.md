# 地图配置器 P0 实现说明

> **状态**：P0 已在 `map-configurator` 源码中落地（主进程 `project-fs` + Tab 化 UI）。下文保留为模块与 IPC 对照清单。

> ~~当前会话处于 **Plan mode**~~（已过时）

---

## 1. 主进程：`src/main/project-fs.ts`（新建）

职责：`resolveSafe`、创建 `assets/`、`export/`、读写 `project.json`、读写 `export/script.json`、导入楼层图到 `assets/floor_1.*`、按相对路径读二进制转 base64。

要点：

- 禁止 `..` 路径穿越。
- `importFloorImage` 用 `dialog.showOpenDialog` + `copyFile`。

## 2. 主进程：`src/main/index.ts`（扩展 IPC）

在现有 `validate-script` / `open-script-file` / `save-script-file` 基础上增加 `ipcMain.handle`：

| channel | 参数 | 行为 |
|---------|------|------|
| `project-select-dir` | 无 | `dialog.showOpenDialog({ properties: ['openDirectory'] })` 返回路径或 cancel |
| `project-ensure-dirs` | `projectRoot: string` | 调 `ensureProjectDirs` |
| `project-read-json` | `projectRoot` | `readProjectJson` |
| `project-write-json` | `projectRoot`, `data: object` | `writeProjectJson` |
| `project-read-export-script` | `projectRoot` | `readExportScript` |
| `project-write-export-script` | `projectRoot`, `jsonText: string` | `writeExportScript` |
| `project-import-floor-image` | `projectRoot` | `importFloorImage` |
| `project-read-file-base64` | `projectRoot`, `relativePath: string` | `readFileBase64` |

## 3. 预加载：`src/preload/index.ts`

`contextBridge.exposeInMainWorld('projectApi', { ... })`，封装上述 invoke。

## 4. 渲染：`src/renderer/src/env.d.ts`

为 `window.projectApi` 补全类型声明。

## 5. 脚本模型（新建建议路径）

| 文件 | 职责 |
|------|------|
| `src/renderer/src/script/types.ts` | `RatioRect`、`Slot`、`Region`、`Trap`、`Wave`、`TowerDefenseScript` 等宽松类型 |
| `src/renderer/src/script/defaultScript.ts` | `createDefaultScript()`：满足 Schema 的最小脚本（含 `origin` region、空 `slots`、一条示例 `waves` 可删） |
| `src/renderer/src/script/constants.ts` | 五类 ROI 的 key 列表：`wave, resource, core_hp, map_ui_indicator, place_error_tip` |

## 6. UI 结构（替换单薄 `App.tsx`）

建议 Tab：**工程 | 元数据 | 地图 | 区域 | 陷阱 | ROI | 波次 | 导出 | JSON**

- **工程**：选目录、`project.json` 读写、显示当前 `projectRoot`；新建时 `ensureProjectDirs` + 默认 `project.json`（含 `floorImageRelative`）。
- **元数据**：绑定 `script_id`、`script_name`、`map.*`、`metadata.author`、`metadata.game_version`（可选）。
- **地图**：导入楼层图 → 存 `assets/floor_1.png`；`img` 的 `src` 用 `data:image/...;base64,`（经 `project-read-file-base64`）；点击图像在**图像像素坐标**上换算 `x_ratio/y_ratio`（相对图片宽高 0–1），追加 `slots` 默认项（`precision`、`verify.check_area` 可抄示例 JSON）。
- **区域 / 陷阱 / ROI**：表格编辑 `regions[]`、`traps[]`、`recognition.rois`。
- **波次**：`wave` + `trigger wave_eq` + `actions` 列表；动作类型 `pan_to_region` | `place_trap` | `log` 的表单字段。
- **导出**：`JSON.stringify(script, null, 2)` → `validate-script` → `project-write-export-script`；保留原「另存为」单文件 `save-script-file` 可选。

## 7. 依赖

P0 可不引 `zustand`，用 `useReducer` + 单文件 `editorReducer.ts` 或 `useState` .lift 到 `App`。

若画布交互复杂再引 `react-konva`（P0 可用原生 `div` + `img` + `click` 坐标）。

## 8. 验收

- `npm run build` 通过。
- 选工程目录 → 导入图 → 点两个 slot → 填 region/trap → 导出 → `python -m td_executor validate export/script.json` 通过。

---

（完）待 Agent mode 开启后，可将本节作为任务清单逐文件实现。
