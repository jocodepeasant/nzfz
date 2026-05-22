# 地图配置器：可视化编辑需求草案 V2（头脑风暴落地）

> 本文档承接 `[tower_defense_automation_design_v1.md](../tower_defense_automation_design_v1.md)` 的总体拆分，把「俯视截图底图 + 空间标注 + 波次/条件/升级拆除」落到**可评审的需求章节**，供配置器与协议迭代使用。  
> 执行器仍以 `[schemas/tower_defense_script_v1.schema.json](../schemas/tower_defense_script_v1.schema.json)` 为契约；本草案中**新增字段均为可选**，旧脚本保持兼容。

---

## 1. 产品目标（相对现状）


| 维度    | V1 骨架（当前） | V2 目标（本草案）                                    |
| ----- | --------- | --------------------------------------------- |
| 空间编辑  | 纯文本 JSON  | **俯视截图底图**上放点、画区域、对齐辅助线                       |
| 时间编排  | 手写 waves  | **波次列表 + 每波动作链**可视化（可折叠 JSON 高级区）             |
| 条件/重试 | 手写        | **表单化常用条件**（波次、资源、槽位空/占）+ 高级 JSON             |
| 楼层    | 未建模       | **两层各一张底图**，对象带 `floor_id`；见第 6 节             |
| 导出    | 单文件 JSON  | **工程目录**（见第 5 节）导出合并后的 `script.json` + 可选资源清单 |


---

## 2. 画布与坐标系

### 2.1 底图与楼层

- 用户从游戏截取**整局俯视地图**；**一层楼一张图**（你已确认的资产形态）。
- 配置器支持在编辑器内**切换楼层**加载对应底图；未切换时编辑对象归属当前楼层。

### 2.2 坐标系（与执行器对齐）

- 协议继续以 `**region_screen_ratio`** 为主：`x_ratio` / `y_ratio` 相对于**游戏窗口客户区**（与 V1 文档一致）。
- **编辑器内**：在底图上点击得到的像素 (px, py)，在「标定后」的矩形内归一化：


x{ratio} = \frac{px - left}{width},\quad y{ratio} = \frac{py - top}{height}


其中 [left, top, width, height] 为**地图内容在窗口中的有效区域**（可因黑边、UI 占位而与整窗不同）。

### 2.3 标定（Calibration，必做需求）

**问题**：截图分辨率 ≠ 对局窗口分辨率；DPI 缩放、黑边、UI 壳会导致比例漂移。

**V2 最小标定流程（建议）**

1. 用户在配置器导入「参考分辨率」下的截图（例如 1920×1080）。
2. 用户在底图上框选**与游戏内地图区域一致**的矩形（四角拖拽），记为 `map_content_rect`（像素，相对于截图）。
3. 导出时写入脚本 `metadata` 或 `map.calibration`（具体字段名实现阶段冻结），执行器用同一套规则把「脚本比例」映射到「当前窗口中的地图矩形」。

**遗漏点显式记录**

- 若局内地图可缩放，需约定「标定基于默认缩放」或增加「缩放档位多套标定」——**V2 先单档位**，多档位列为后续。
- 槽位坐标是**相对全图截图**还是**相对某 region 视野**：与 V1 的 `slot.region_id` + `position` 语义一致时，应约定：**数值为「进入该 region 后的地图客户区比例」**；配置器在 UI 上可按 region 裁剪显示，导出仍写全局脚本结构（与现协议一致）。

### 2.4 ROI 与 HUD 是什么？（名词）

- **ROI（Region of Interest，感兴趣区域）**：在**整屏画面**里框出来的一小块矩形（用比例坐标存：`x_ratio, y_ratio, w_ratio, h_ratio`）。执行器每次截图后，只裁这一块送给 OCR 或图像算法，**减少计算量、减少无关像素干扰**。例如：波次数字在右上角一小块，就只认那一块。
- **HUD（Heads-Up Display，抬头显示 / 游戏 UI 层）**：叠在游戏画面上方的**血条、资源、提示字、按钮**等界面层。塔防里「地图」可能被 HUD 挡住边缘；你截的俯视「地图」有时也带 HUD 条。

### 2.5 ROI 怎么组织：「各自独立 ROI」vs「大 HUD + 子区域」

这是**数据建模与编辑器交互**的选择，不是游戏里的物理概念。

| 方案 | 含义 | 适用 |
|------|------|------|
| **各自独立 ROI** | 每个识别目标（波次、资源、某条 UI 文案、放置错误提示）各有一个**小矩形**，互不嵌套。执行器按名字取对应矩形裁剪。 | 元素在屏幕上位置**相对固定**、彼此离得远；实现简单，**推荐作为默认**。 |
| **大 HUD + 子区域** | 先框一个**大的**「整个上沿 HUD」父矩形，再在父矩形内定义**相对坐标**的子 ROI（或像素偏移）。 | HUD 整体会**左右平移**或缩放，但内部相对布局稳定；子 ROI 跟着父区域一起动。 | 实现复杂；适合后期「整 HUD 漂移」明显时再加。 |

**建议**：V2 识别配置以**独立 ROI 列表**为主；若某几条 UI 总是一起动，再在 `recognition` 里增加可选 `hud_group` 结构（后续版本）。

### 2.6 「全图截图标定」和「局内窗口标定」两套是啥？（详细）

你手上有两类「图」：

1. **全图俯视截图**：你在游戏外或地图全开时截的**一整张战略地图**（配置器里当底图，用来**点 slot、画 region**）。
2. **局内实时窗口**：自动化跑的时候，游戏是一个**窗口**，里面是**可拖拽的局部视野**，周围还有黑边、边框、比例缩放。

**问题**：在 (1) 上点的比例坐标，不能不经转换就当成 (2) 里「当前这一帧窗口」的同一个点——因为视野会拖、缩放会变、黑边会占像素。

**两套标定**指的就是为这两类几何关系各存一套参数（或一条变换链）：

- **全图标定（编辑器用）**：底图像素 → 「逻辑全图」上的归一化坐标（你画 slot 用）。
- **局内窗口标定（执行器用）**：游戏窗口客户区 → 「当前地图内容矩形」→ 再映射到点击坐标（你点游戏用）。

**V2 务实做法**：配置器仍以**比例坐标 + map.calibration** 描述「地图内容在参考窗口中的矩形」；执行器用**同一套比例语义**映射到**实时窗口**（文档 §2.3 的 `map_content_rect` 思路）。**不要求**用户在配置器里再画一遍「局内每一种视野」；若某地图拖拽极大，再通过 `regions` / `pan_to_region` 把视野对齐到可重复状态。

---

## 3. 对象模型（编辑器 ↔ JSON 映射）


| 编辑器对象     | 脚本中的主要承载                       | 说明                                                  |
| --------- | ------------------------------ | --------------------------------------------------- |
| 楼层 Floor  | `map.floors[]`（可选）+ 当前编辑上下文    | 每层独立底图与可选 `base_resolution`                         |
| 区域 Region | `regions[]` + `enter_actions`  | 折线/多段 pan 后续可做；V1 仍为 `pan_map` 序列                   |
| 槽位 Slot   | `slots[]`                      | 绑定 `region_id`、`trap_id` 默认、校验区 `verify.check_area` |
| ROI       | `recognition.rois`             | 矩形框在底图/窗口示意层上画，导出比例                                 |
| 陷阱定义      | `traps[]`（导出写入 `export/script.json`） | 编辑器侧维护于 **map-configurator/traps/**（应用级，非工程目录）；导出时合并花费/升级等；可选 `recognition_template` |
| 波次        | `waves[]`                      | `trigger` + 有序 `actions`                            |
| 动作        | `actions[]` 内 `type` 分支        | place / upgrade / remove / pan_to_region / log 等    |
| 条件 / 重试   | `conditions`、`retry`、`on_fail` | MVP 先覆盖文档已有字段                                       |


**关系约束（校验规则草案）**

- 每个 `slot.region_id` 必须存在于 `regions`。
- 每个 `place_trap.slot_id` 必须存在于 `slots`。
- 若存在 `map.floors`，则每个 `region`、`slot` 的 `floor_id` 必须能在 `floors` 中找到；未写 `floor_id` 时默认 `map.default_floor_id`（见第 6 节 Schema 说明）。

### 3.1 动作矩阵（主体 × 语义 × 条件 × 验证）

下表固定**语义**，避免配置器与执行器对「升级 / 拆除」理解不一致。JSON 里可表现为**不同 `type`**，或单一 `type` + `scope` 字段——实现阶段冻结一种即可。

| 动作意图 | 建议 `type`（草案） | 作用主体 | 典型前置条件 | 典型验证 `verify` | 备注 |
|---------|-------------------|---------|-------------|------------------|------|
| 放置陷阱 | `place_trap` | **slot**（`slot_id`） | `resource_gte`、`slot_empty`、波次等 | `slot_has_trap` | 需先 `pan_to_region` 进入区域（若 slot 绑定了 region） |
| 按类型升级 | `upgrade_trap` | **陷阱类型**（`trap_id`） | `resource_gte`、`trap_level_lt` 等 | `trap_level_gte`（可选） | 与 `upgrade_mode: all_same_type` 一致；**不是**点某一格为主语义 |
| 拆除单个 | `remove_trap` | **slot**（`slot_id`） | `slot_occupied`、波次等 | `slot_empty` | 需定位到该格曾放置的位置 |
| 按类型拆除全部 | `remove_trap_by_type`（或 `remove_trap` + `scope: all_matching`） | **陷阱类型**（`trap_id`） | 波次、资源、UI 阶段等 | 可组合多次 slot 校验或模板匹配（后续） | 与「拆一格」分叉，配置器 UI 分两条向导 |

**执行顺序约定（草案）**：`switch_floor`（若需要）→ 确保地图 UI 打开 → `pan_to_region` → 读条件（事件驱动见第 9 节）→ 执行动作 → 验证 → 重试/降级。

---

## 4. 动作生命周期（编辑器编排视角）

### 4.1 放置 `place_trap`

1. 选陷阱（来自 `traps`）→ 选槽位（来自 `slots`，可按楼层筛选）。
2. 配置 `conditions`（MVP：`resource_gte`、`slot_empty`）。
3. 配置 `verify` / `retry` / `on_fail`（MVP：预设模板 + 可展开高级项）。

### 4.2 升级 `upgrade_trap`

- 与文档一致：`upgrade_mode: all_same_type` 表示**按陷阱类型全局升级**；配置器 UI 应用文案说明，避免用户误以为是「点某一格」。
- MVP：表单选 `trap_id`、`target_level`、`resource_gte`、`hold_ms` 默认值来自 `trap.upgrade_hold_ms`。

### 4.3 拆除 `remove_trap` / 按类型拆除

- **拆单个**：`remove_trap`，主体为 `slot_id`；`execute.method` 可为占位 `custom_steps` 或后续按键宏。
- **按陷阱类型拆全部**：单独动作（见 §3.1 矩阵），避免与 slot 级语义混用；实现前在 Schema 中新增类型或 `scope` 枚举。

### 4.4 区域进入 `pan_to_region`

- 选 `region_id`；展示该区域 `enter_actions` 预览（只读），编辑仍走表单或 JSON。

### 4.5 触发与时间轴

- **主时间轴**：仍以 `waves[].trigger` 为主（如 `wave_eq`）。
- **扩展（非 MVP）**：`resource_gte` 跨波触发、`timer` 等——后续 schema 小版本引入。
- **BOSS 血条、BOSS 阶段识别**：**本阶段不做**；协议继续保留 `boss_reserved`，执行器仅占位，避免配置器与脚本字段冲突。

### 4.6 切层（楼层切换）

- **交互**：按**数字键**切换楼层，**数字键值表示第几层**（如 `1` → 第一层，`2` → 第二层；与游戏内实际绑定关系在脚本 `metadata` 或 `runtime` 中可配置键位映射）。
- **与 `floor_id` 对齐**：配置器为对象标注 `floor_id`；执行器在跨层动作前插入「切层」步骤（具体动作名 `switch_floor` 或宏序列，实现阶段冻结）。

---

## 5. 工程结构与导出

### 5.1 建议目录（配置器工程，非脚本必须）

```text
MyMap.nzmap/   （用户工程，实际可为任意文件夹名）
├── project.json          # 楼层、标定、槽位默认等；不含 traps[]（陷阱库与工程解耦）
├── assets/
│   ├── floor_1.png
│   └── floor_2.png
└── export/
    └── script.json       # 导出给执行器（通过 Schema 校验）

map-configurator/   （应用安装/开发目录，与上述工程无关）
├── traps/                  # 陷阱定义 traps/{trap_id}.json
└── assets/verify_templates/  # 陷阱识别图 trap_{trap_id}.*
```

- `**project.json**`：允许包含执行器**不需要**的字段（仅配置器使用）；**陷阱库不写入** `project.json`，保存时剥离 `traps`。
- `**export/script.json`**：必须满足 Schema；`traps[]` 来自应用陷阱库；若陷阱配置了识别图，对应项含可选字段 `recognition_template`（路径相对 **map-configurator** 根，如 `assets/verify_templates/trap_trap_a.png`）。配置器 UI 不编辑 `select_key`/`upgrade_key` 时，导出默认均为 `"1"`。CI 与配置器内置「导出前校验」。

### 5.2 与 Git 协作

- 大图二进制建议使用 **Git LFS** 或仓库存图策略由团队自定；文档层保持 JSON/ YAML 可读 diff 更友好。

---

## 6. 楼层与脚本协议（评估结论）

**结论**：采用 `**map.floors[]` + 可选 `floor_id` 贯穿 `regions` / `slots`**，而不是顶层并列两份完整 `script`。理由：

1. **单文件交付**：执行器仍加载一份 `script.json`，逻辑集中。
2. **与 V1 兼容**：旧脚本无 `floors`、无 `floor_id` 时，语义与「单层楼」一致。
3. **与你选定的资产模型一致**：两层各一张图 → 放在 `floors[].editor_reference_image`（或 `metadata.floor_assets`）供配置器还原；执行器可忽略该字段，仅消费 `floor_id` 与坐标。

**执行器侧（说明性）**

- 执行器在动作前需知晓「当前游戏内楼层」；**切层按数字键（第 N 层按 N）** 作为默认策略写入脚本（可配置键位表）；与 `floor_id` 对齐通过显式前置动作完成。

**Schema 变更**：已在 `[schemas/tower_defense_script_v1.schema.json](../schemas/tower_defense_script_v1.schema.json)` 增加可选 `map.floors`、`map.default_floor_id`，以及 `region.floor_id` / `slot.floor_id`（可选）。

---

## 7. 配置器 MVP 定义（实现排期参考）

**目标**：一人可在一小时内从「空工程」到「导出可校验脚本（含一张底图上的若干槽位与一波放置链）」。

### 7.1 MVP 必含

1. **导入楼层底图**（至少一层；二层可只显示「待导入」占位）。
2. **在底图上放置 Slot**：点击生成点，侧栏编辑 `slot_id`、`name`、`region_id`（可从下拉选已有 region）、`default_trap`。
3. **简易 Region 列表**：表格新增一行 `region_id` + 名称；`enter_actions` 先支持 0～1 段 `pan_map` 表单或 JSON 文本框。
4. **波次编辑器（单波 MVP）**：选一个 `wave` 序号，`trigger.type = wave_eq` + 数值；动作为有序列表，**MVP 仅支持** `pan_to_region`、`place_trap`、`log`（upgrade/remove 通过「高级：原始 JSON 片段」或第二阶段表单接入）。
5. **导出**：写出 `export/script.json` 并调用 Ajv 校验；错误列表可定位到对象 ID。
6. **打开已有 `script.json`**：反解析为「底图 + 点」的尽力还原（无 project 时仅展示表格与 JSON，不强行对齐像素）。

### 7.2 MVP 明确不做

- 多边形区域绘制、自动寻路、BOSS 条件链、模板匹配可视化全流程。
- 与执行器真实联调（另列集成测试项）。

### 7.3 第二阶段（Post-MVP）

- `upgrade_trap` / `remove_trap` / `remove_trap_by_type`（或等价 `scope`）全表单化；从底图裁切 `verify` 模板；`switch_floor` 动作与按键宏编辑器；tile 网格吸附。
- **模板库**：常用 ROI、`pan_map` 段、「等钱」条件块的可插入片段（见 §9.9）。

---

## 8. E2E 验收用例（草案）


| ID  | 步骤                                                                                                                                  | 期望                                            |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| E1  | 新建工程 → 导入 `floor_1.png` → 标定地图矩形 → 放置 2 个 slot → 绑定同一 region → 导出                                                                   | `script.json` 通过 Schema；`slots` 长度为 2；比例在 0–1 |
| E2  | 打开 `[schemas/examples/space_station_normal_baseline_v1.json](../schemas/examples/space_station_normal_baseline_v1.json)` → 校验 → 再导出 | 与原始语义一致（允许格式化差异）；校验无错误                        |
| E3  | 为 `map.floors` 增加两层元数据（可选图路径）→ 给 slot 指定不同 `floor_id` → 导出                                                                          | Schema 通过；执行器侧 dry-run 仍可通过（未实现楼层逻辑时不应崩溃）     |


---

## 9. 识别管线与对局外围（2026-05 共识）

### 9.1 ROI 清单与优先级（在 V1 已有 ROI 上扩展）

**保留 V1 已有**（名称与用途对齐设计文档）：`wave`、`resource`、`core_hp`、`map_ui_indicator`、`place_error_tip`。

**本阶段新增（必选能力）**

| ROI 名称（草案） | 用途 |
|-----------------|------|
| `ui_text_primary` | 主提示 / 结算类**单行**文案 OCR（可多实例时见下节「实例化」） |
| `ui_text_secondary` | 副提示区（可选） |

**BOSS 血条 / BOSS 信息条**

- **本阶段不做识别与条件**；与 `boss_reserved` 一致，仅保留字段与 UI 占位，后续版本再接入。

**多实例 UI 文案条**

- 若同屏多条提示位置不固定：采用 `ui_text_slots[]` 数组，每项含 `id` + `ratioRect`；条件里引用 `ui_text_slots[id]` 的识别结果。具体 Schema 在实现前再冻结。

### 9.2 识别触发：**事件驱动**

- 不在空闲时固定高频轮询全屏；在**波次变化**、**动作前后**、**条件等待超时前唤醒**、**用户定义的离散事件点**触发采样与 OCR。
- 仍需定义**最小采样间隔**（防抖）与**同一事件上的多帧投票**（沿用 `recognition.multi_frame` 思路）。

### 9.3 UI 文案识别输出：「原始字符串 + 置信度」vs「关键词 / 正则」

| 方式 | 是什么 | 优点 | 缺点 |
|------|--------|------|------|
| **原始字符串 + 置信度** | OCR 返回文本 + 引擎置信度；条件里可做 `contains` / `levenshtein` 模糊匹配 | 灵活、易调试（日志里可见原文） | 字体特效、半透明时置信度波动大 |
| **关键词 / 正则** | 在 OCR 结果或二值化后的字符串上做**子串或模式匹配** | 对轻微识别错误更鲁棒；适合做「出现胜利/失败关键字」 | 正则写错易误判；需约定大小写/全半角 |

**结论**：协议与执行器**两种都支持**；配置器条件表单可提供「包含」「正则匹配」「模糊距离阈值」三档，由脚本作者选用。调试模式日志默认打**原始字符串 + 置信度**。

### 9.4 失败与降级（待继续细化，先立骨架）

以下条目作为**下一轮讨论清单**，实现时落在 `runtime` / 各动作的 `on_fail` / 全局 `policy`：

- **OCR 失败**：连续 N 次低置信度 → 重试间隔加倍 → 超过阈值 → `skip` / `abort_wave` / `abort_run`。
- **条件长期不满足**：`wait` + 超时 → `skip` / `retry_condition` / 人工暂停（若接调试）。
- **地图 UI 丢失**：按 O 重开 → 回 origin → 再继续；次数上限。
- **UI 文案与预期不符（胜负）**：仅依赖 UI 文案阶段 → 进入「未知状态」分支：记录截图、中止或重试整段（策略待定）。

**默认策略（已讨论）**：未知胜负文案时，采用**固定时间窗内重试识别 N 次**，仍不匹配再 **abort_run**（具体 N 与窗口写入 `runtime`，默认值实现阶段冻结）。

### 9.5 胜负 / 结算判定（阶段结论）

- **暂时只考虑 UI 文案**：例如胜利/失败/重试提示出现在 `ui_text_*` ROI 内即判定；不引入独立「结算面板 ROI」直至有需求。

### 9.6 暂停 / 弹窗 / 遮罩

- **纳入需求但不实现**：设计为**执行器通用模块**（检测全屏遮罩、常见弹窗按钮、点击关闭或等待）；配置器侧预留「遇到遮罩时策略」钩子即可。

### 9.7 地图 / 难度 / 策略矩阵

- **先一份脚本**：单地图、单难度、单策略；多组合通过**多份工程/多份 script** 扩展，后续再讨论「单工程多 profile」。

### 9.8 版本与回归测试

- 游戏小版本导致 UI 偏移时，脚本**半自动失效**难以完全检测；方向性措施：**导出时记录依赖的游戏版本号**（人工填）、**固定几条 smoke 脚本**在 CI 或每日机上跑截图 diff（成本高，**不强制 MVP**）。

### 9.9 模板库（同意）

- 配置器支持**片段库**：常用 ROI 集合、常用 `pan_map` 段、常用「等钱 / 等波」条件块，可插入到当前波次或工程；存储为 `snippets/*.json` 或 `project.json` 引用。

---

## 10. 地图配置器：模块拆分与优先级

**优先级说明**

| 级别 | 含义 |
|------|------|
| **P0** | 首版可交付（MVP）：无则无法完成「底图 → 槽位 → 波次 → 导出可校验脚本」闭环 |
| **P1** | 紧随其后的短迭代：显著提升可用性或与已讨论语义强相关 |
| **P2** | 中长期：体验增强、复杂标注、与执行器深度联动或非阻断能力 |

**模块总表**

| 编号 | 模块 | 子能力（拆分） | 优先级 | 依赖 / 备注 |
|------|------|----------------|--------|-------------|
| M1 | **工程与文件** | 新建 / 打开 / 保存工程目录；`project.json` 读写；资源路径相对化 | **P0** | 与 §5 目录结构一致 |
| M2 | **脚本元数据** | `script_id`、`script_name`、`map_id`、难度、策略、作者、版本备注（可选 `game_version` 人工填） | **P0** | 导出写入 `metadata` / `map` |
| M3 | **画布与楼层** | 单楼层底图导入、缩放平移；楼层切换（两张图）；当前编辑 `floor_id` 上下文 | **P0**（单图） / **P1**（双图切换） | 双图与 `map.floors` 对齐 |
| M4 | **标定** | `map_content_rect` 或等价四角框选；写入 `map.calibration`；预览映射 | **P1** | P0 可先「整图即地图」简化，有偏差再上 |
| M5 | **槽位 Slot** | 底图上放点；侧栏编辑 `slot_id`、`name`、`region_id`、`default_trap`、`floor_id`；删除 / 列表 | **P0** | 依赖 M3、M6 |
| M6 | **区域 Region** | 表格 CRUD；`enter_actions` 至少 0～1 段 `pan_map` 表单或 JSON | **P0** | 先于或与 M5 并行 |
| M7 | **陷阱 Traps** | 应用级陷阱库全页：`traps/{trap_id}.json` + 识别图；导出 `traps[]`（花费、升级模式；可选 `recognition_template`；键位 UI 省略时导出默认 `1`） | **P0** | 供槽位/波次下拉；与工程目录解耦 |
| M8 | **识别 ROI** | V1 五类 ROI 矩形编辑；导出 `recognition.rois` | **P0** | 可与底图画布分屏或标签页 |
| M8b | **UI 文案 ROI** | `ui_text_primary` / `ui_text_secondary`；可选多实例 `ui_text_slots[]` | **P1**（先主区） / **P2**（多实例 Schema） | 与 §9.1 一致 |
| M9 | **波次与动作** | `wave_eq` 触发；动作链：`pan_to_region`、`place_trap`、`log` | **P0** | 动作矩阵 §3.1 |
| M9b | **升级 / 拆除** | `upgrade_trap` 表单（按类型）；`remove_trap`（slot）；`remove_trap_by_type` 或 `scope`（与 Schema 冻结后一致） | **P1** | P0 可用「高级 JSON」过渡 |
| M10 | **条件与失败策略** | 常用条件表单：`resource_gte`、`slot_empty`、`slot_occupied`；`on_condition_failed` / `retry` / `on_fail` 预设模板 | **P0**（最小集） / **P1**（扩展 + UI 文案条件） | 与执行器条件引擎对齐 |
| M11 | **校验与导出** | Ajv 校验、错误定位；写出 `export/script.json`；可选「仅校验」 | **P0** | 已有骨架能力 |
| M12 | **打开已有脚本** | 导入 `script.json`；表格 + JSON 双视图；尽力还原 slot 点（无 project 时） | **P1** | 降低从手写迁移成本 |
| M13 | **模板库** | 片段插入：ROI 组、`pan_map`、`等钱/等波` 条件块；`snippets/` 或工程内引用 | **P2** | §9.9，依赖 M8/M9/M10 成熟 |
| M14 | **验证资源（裁切）** | 从底图裁切 `verify` 参考块、导出路径；模板匹配参数 | **P2** | 与执行器 vision 联动 |
| M15 | **BOSS 占位** | UI 勾选/说明写入 `boss_reserved`；无逻辑 | **P2** | 仅占位，§9.1 |

**推荐实现顺序（迭代线）**

1. **Sprint A（P0 闭环）**：M1 → M2 → M3（单图）→ M6 → M7 → M5 → M8 → M9（仅 pan/place/log）→ M10（最小条件）→ M11。  
2. **Sprint B（P1 对齐讨论）**：M3 双图 + `floor_id`；M4 标定；M8b；M9b；M12；M10 扩展 UI 文案条件（执行器侧就绪后接）。  
3. **Sprint C（P2）**：M13 → M14 → M15 及多边形区域、HUD 组合 ROI 等。

**与执行器的边界（配置器不做）**

- 事件驱动 OCR 采样、胜负判定逻辑、暂停弹窗处理、真实键鼠注入：归 **automation-executor**；配置器只生成协议内字段与 ROI 几何。

---

## 11. 开放问题（待细化）

- **失败与降级**：各分支默认策略（§9.4）需与你们能接受的风险（误点、死循环）对齐。
- **多实例 UI 文案**：是否必须首版就支持 `ui_text_slots[]`，还是先单一 `ui_text_primary`。
- **`remove_trap_by_type` 与 Schema**：与现有 `remove_trap` 分叉的字段形态待冻结。

---

## 12. 文档与代码索引


| 资源                   | 路径                                                                                              |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| 总体 V1 设计             | `[tower_defense_automation_design_v1.md](../tower_defense_automation_design_v1.md)`             |
| 脚本 Schema            | `[schemas/tower_defense_script_v1.schema.json](../schemas/tower_defense_script_v1.schema.json)` |
| 配置器 README（含 MVP 摘要） | `[map-configurator/README.md](../map-configurator/README.md)`                                   |


