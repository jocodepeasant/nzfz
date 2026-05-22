# 《逆战：未来》塔防自动化通关测试系统需求与架构设计 V1.0

## 1. 文档说明

本文档用于描述《逆战：未来》塔防模式自动化通关测试系统的 V1.0 需求、架构设计、模块划分、技术栈建议，以及地图配置器与自动化执行器之间的脚本 JSON 协议。

系统拆分为两个核心子系统：

1. **地图配置器**：负责配置地图、陷阱、区域、格子、波次动作，并导出脚本 JSON。
2. **自动化执行器**：负责读取脚本 JSON，在游戏对局内执行自动化操作。

两者之间只通过脚本 JSON 通信，可以并行开发。

---

## 2. 版本范围

### 2.1 V1.0 目标

V1.0 主要实现：

- 支持 1920×1080 优先适配；
- 设计上支持其他分辨率；
- 支持单地图、单难度、单策略脚本；
- 支持地图配置器生成 JSON；
- 支持执行器读取 JSON 并执行；
- 支持按波次执行动作；
- 支持放置陷阱、升级陷阱、拆除陷阱；
- 支持条件判断；
- 支持失败重试；
- 支持批量跑固定脚本；
- BOSS 专项逻辑仅预留模块。

### 2.2 V1.0 暂不做

- BOSS 专项复杂处理；
- 多人协同自动化；
- 动态智能策略；
- 多脚本队列批量调度；
- 完整地图世界坐标自动寻路；
- 自动学习最优通关策略。

---

## 3. 总体架构设计

### 3.1 总体架构

```text
地图配置器
  ├── 脚本基础信息配置
  ├── 识别区域配置
  ├── 陷阱配置
  ├── 地图区域配置
  ├── 陷阱格子配置
  ├── 波次动作配置
  ├── 条件与失败策略配置
  └── 导出脚本 JSON
             ↓
        脚本 JSON 协议
             ↓
自动化执行器
  ├── 脚本加载与校验
  ├── 游戏窗口管理
  ├── 屏幕采集
  ├── OCR / 图像识别
  ├── 状态管理
  ├── 条件判断
  ├── 地图区域导航
  ├── 动作执行
  ├── 失败重试
  ├── 日志报告
  └── 批量跑局
```

### 3.2 设计原则

| 原则 | 说明 |
|---|---|
| 配置与执行解耦 | 配置器只生成 JSON，执行器只消费 JSON |
| 地图适配配置化 | 新地图尽量通过配置器适配，不改执行代码 |
| 坐标比例化 | 坐标以比例形式保存，适配不同分辨率 |
| 动作原子化 | 放置、升级、拆除、等待、拖拽均抽象为动作 |
| 条件驱动 | 所有关键动作执行前必须判断条件 |
| 可重试 | 放置失败、拖拽失败、识别失败可重试 |
| 可扩展 | BOSS、队列、多策略等功能预留扩展点 |

---

## 4. 技术栈建议

### 4.1 地图配置器技术栈

#### 推荐方案 A：桌面端应用

| 层级 | 技术 |
|---|---|
| UI 框架 | Electron + React / Vue |
| 语言 | TypeScript |
| 状态管理 | Zustand / Pinia |
| 图像标注 | Canvas / Konva.js / Fabric.js |
| JSON Schema 校验 | Ajv |
| 本地文件 | Node.js fs API |
| 打包 | Electron Builder |

优点：

- 适合做截图标注；
- 文件读写方便；
- 可直接导入/导出 JSON；
- UI 开发效率高。

#### 推荐方案 B：Web 工具

| 层级 | 技术 |
|---|---|
| 前端 | React / Vue |
| 图像标注 | Canvas / Konva.js |
| Schema 校验 | Ajv |
| 文件导出 | Blob / FileSaver |

适合内部网页化工具，但本地截图和文件管理能力弱于 Electron。

### 4.2 自动化执行器技术栈

| 模块 | 推荐技术 |
|---|---|
| 主语言 | Python 3.10+ |
| GUI 自动化 | pyautogui / pynput / pywin32 |
| 窗口管理 | pywin32 |
| 截图 | mss / dxcam |
| OCR | PaddleOCR / EasyOCR / Tesseract |
| 图像处理 | OpenCV |
| 模板匹配 | OpenCV matchTemplate |
| 配置校验 | jsonschema / pydantic |
| 日志 | logging / loguru |
| 报告 | JSON / CSV / HTML |
| 打包 | PyInstaller |

### 4.3 执行器技术选型建议

#### 截图方案

优先级：

1. `dxcam`：适合游戏窗口高频截图；
2. `mss`：通用稳定；
3. `pyautogui.screenshot`：简单但性能较弱。

#### OCR 方案

推荐优先：

- PaddleOCR：中文与数字识别效果较好；
- 对数字类 ROI 可做专门预处理；
- 对波次、资源、血量使用固定 ROI + 正则校验。

#### 图像识别方案

推荐：

- OpenCV 模板匹配；
- 颜色区域检测；
- 图像差分；
- 多帧投票。

---

## 5. 模块划分

### 5.1 地图配置器模块

| 模块 | 职责 |
|---|---|
| Project Manager | 新建、打开、保存脚本项目 |
| Metadata Editor | 编辑地图、难度、策略等基础信息 |
| ROI Editor | 标注 OCR / 图像识别区域 |
| Trap Editor | 配置陷阱、按键、消耗、升级参数 |
| Region Editor | 配置地图区域及拖拽路径 |
| Slot Editor | 标注陷阱格子及校验区域 |
| Wave Editor | 配置每波动作 |
| Condition Editor | 配置动作执行条件 |
| Retry Editor | 配置失败重试策略 |
| JSON Preview | 预览生成 JSON |
| Schema Validator | 校验 JSON 合法性 |
| Exporter | 导出脚本 JSON |

### 5.2 自动化执行器模块

| 模块 | 职责 |
|---|---|
| Script Loader | 加载脚本 JSON |
| Script Validator | 校验脚本协议 |
| Window Manager | 定位游戏窗口 |
| Coordinate Mapper | 比例坐标转换为实际坐标 |
| Screen Capture | 获取游戏画面 |
| OCR Engine | 识别波次、资源、血量 |
| Vision Detector | 识别地图界面、格子状态、错误提示 |
| State Manager | 管理游戏状态 |
| Condition Engine | 判断动作执行条件 |
| Region Navigator | 执行地图拖拽进入区域 |
| Slot Locator | 定位和点击陷阱格子 |
| Action Executor | 执行放置、升级、拆除等动作 |
| Retry Manager | 处理动作失败重试 |
| Report Manager | 生成日志和报告 |
| Batch Runner | 批量跑局 |

---

## 6. 地图配置器需求设计 V1.0

### 6.1 模块定位

地图配置器用于生成一份单地图、单难度、单策略的自动化通关脚本 JSON。

配置器不直接操作游戏，只负责配置和导出。

### 6.2 配置器核心功能

地图配置器需要支持：

1. 创建脚本；
2. 配置地图基础信息；
3. 配置识别区域；
4. 配置陷阱列表；
5. 配置地图区域；
6. 配置陷阱格子；
7. 配置每个波次动作；
8. 配置动作条件；
9. 配置失败策略；
10. 导出 JSON；
11. 校验 JSON。

### 6.3 配置器页面

建议页面：

1. 脚本基础信息页；
2. 识别区域配置页；
3. 陷阱配置页；
4. 地图区域配置页；
5. 陷阱格子配置页；
6. 波次动作配置页；
7. 条件与失败策略配置页；
8. JSON 预览页；
9. JSON 校验与导出页。

### 6.4 配置器验收标准

| 项目 | 标准 |
|---|---|
| 创建脚本 | 支持 |
| 配置地图和难度 | 支持 |
| 配置 ROI | 支持 |
| 配置陷阱 | 支持 |
| 配置 region | 支持 |
| 配置 slot | 支持 |
| 配置 wave actions | 支持 |
| 配置条件 | 支持 |
| 配置失败策略 | 支持 |
| 导出 JSON | 支持 |
| JSON 校验 | 支持 |

---

## 7. 自动化执行器需求设计 V1.0

### 7.1 模块定位

自动化执行器负责读取地图配置器导出的脚本 JSON，在游戏对局内执行对应自动化动作。

执行器负责通用流程：

- 进入对局后的初始化；
- 按 O 打开陷阱地图；
- 判断是否在地图界面；
- 回到地图初始视野；
- 识别波次、资源、血量；
- 执行波次动作；
- 放置、升级、拆除陷阱；
- 条件判断；
- 失败重试；
- 结算处理；
- 批量跑局。

### 7.2 执行器主流程

```text
加载脚本 JSON
  ↓
校验脚本合法性
  ↓
等待进入对局
  ↓
检测是否在陷阱地图界面
  ↓
如果不在，按 O 打开
  ↓
记录初始视野为 origin
  ↓
循环识别波次 / 资源 / 血量 / 结算状态
  ↓
匹配当前 wave
  ↓
按顺序执行 wave.actions
  ↓
每个动作执行前检查 conditions
  ↓
条件不满足则按 on_condition_failed 处理
  ↓
动作失败则按 retry / on_fail 处理
  ↓
等待下一波或下一触发条件
  ↓
识别胜利 / 失败 / 异常
  ↓
处理结算
  ↓
生成单局报告
```

### 7.3 地图界面处理

第一次进入对局后：

```text
检测 map_ui_indicator
  ↓
如果不在地图界面
  ↓
按 O
  ↓
等待地图打开
  ↓
再次检测 map_ui_indicator
  ↓
成功后记录为 origin
```

动作前：

```text
执行任意局内动作前
  ↓
检测是否在地图界面
  ↓
如果不在，则按 O 打开
```

### 7.4 回原点策略

由于按 O 后视野固定，V1.0 推荐：

```text
关闭地图
  ↓
重新按 O 打开地图
  ↓
等待稳定
  ↓
当前视野视为 origin
```

### 7.5 坐标转换

V1.0 使用 `region_screen_ratio`：

```text
actual_x = window_left + window_width  × x_ratio
actual_y = window_top  + window_height × y_ratio
```

### 7.6 放置陷阱流程

```text
1. 确保地图界面打开
2. 根据 slot_id 找到 slot
3. 进入 slot 所属 region
4. 检查 conditions
5. 资源不足则默认等待
6. 按 trap.select_key 选择陷阱
7. 点击 slot.position
8. 等待放置结果
9. 校验 slot_has_trap
10. 失败则重试
11. 写入日志
```

### 7.7 升级陷阱流程

```text
1. 确保地图界面打开
2. 根据 trap_id 找到陷阱配置
3. 检查 conditions
4. 资源不足则默认等待
5. 长按 trap.upgrade_key，默认约 4000ms
6. 等待升级完成
7. 可选识别等级标识
8. 失败则重试
9. 写入日志
```

### 7.8 拆除陷阱流程

```text
1. 确保地图界面打开
2. 根据 slot_id 进入对应 region
3. 检查 conditions
4. 按 execute.method 执行拆除
5. 等待拆除完成
6. 校验 slot_empty
7. 失败则重试
8. 写入日志
```

### 7.9 执行器验收标准

| 项目 | 标准 |
|---|---|
| 加载 JSON | 支持 |
| 校验 JSON | 支持 |
| 识别波次 | 支持 |
| 识别资源 | 支持 |
| 判断地图界面 | 支持 |
| 按 O 打开地图 | 支持 |
| 回 origin | 支持 |
| pan_to_region | 支持 |
| place_trap | 支持 |
| upgrade_trap | 支持 |
| remove_trap 抽象 | 支持 |
| 条件判断 | 支持 |
| 失败重试 | 支持 |
| 单局日志 | 支持 |
| 批量跑固定脚本 | 支持 |

---

## 8. 脚本 JSON 协议 V1.0

### 8.1 顶层结构

```json
{
  "schema_version": "1.0.0",
  "script_id": "space_station_normal_baseline_v1",
  "script_name": "空间站普通基础通关脚本",
  "game_mode": "tower_defense",
  "map": {},
  "runtime": {},
  "recognition": {},
  "traps": [],
  "regions": [],
  "slots": [],
  "waves": [],
  "boss_reserved": {},
  "metadata": {}
}
```

### 8.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| schema_version | string | 是 | 协议版本 |
| script_id | string | 是 | 脚本唯一 ID |
| script_name | string | 是 | 脚本名称 |
| game_mode | string | 是 | 固定为 `tower_defense` |
| map | object | 是 | 地图信息 |
| runtime | object | 是 | 运行参数 |
| recognition | object | 是 | 识别区域配置 |
| traps | array | 是 | 陷阱配置 |
| regions | array | 是 | 地图区域配置 |
| slots | array | 是 | 陷阱格子配置 |
| waves | array | 是 | 波次动作配置 |
| boss_reserved | object | 否 | BOSS 预留 |
| metadata | object | 否 | 元信息 |

---

## 9. 完整脚本 JSON 示例

```json
{
  "schema_version": "1.0.0",
  "script_id": "space_station_normal_baseline_v1",
  "script_name": "空间站普通基础通关脚本",
  "game_mode": "tower_defense",
  "map": {
    "map_id": "space_station",
    "map_name": "空间站",
    "difficulty": "normal",
    "strategy_id": "baseline",
    "base_resolution": {
      "width": 1920,
      "height": 1080
    },
    "coordinate_mode": "region_screen_ratio",
    "initial_view": {
      "type": "fixed_after_open_map",
      "origin_region_id": "origin"
    }
  },
  "runtime": {
    "max_run_minutes": 30,
    "default_action_timeout_ms": 8000,
    "default_retry_count": 2,
    "default_resource_policy": "wait",
    "default_wait_resource_timeout_ms": 30000,
    "wait_after_pan_ms": 800,
    "wait_after_place_ms": 600,
    "wait_after_remove_ms": 600,
    "wait_after_upgrade_ms": 1000,
    "reset_view_on_retry": true
  },
  "recognition": {
    "rois": {
      "wave": {
        "x_ratio": 0.42,
        "y_ratio": 0.03,
        "w_ratio": 0.12,
        "h_ratio": 0.04
      },
      "resource": {
        "x_ratio": 0.72,
        "y_ratio": 0.03,
        "w_ratio": 0.10,
        "h_ratio": 0.04
      },
      "core_hp": {
        "x_ratio": 0.48,
        "y_ratio": 0.08,
        "w_ratio": 0.12,
        "h_ratio": 0.04
      },
      "map_ui_indicator": {
        "x_ratio": 0.02,
        "y_ratio": 0.02,
        "w_ratio": 0.12,
        "h_ratio": 0.08
      },
      "place_error_tip": {
        "x_ratio": 0.30,
        "y_ratio": 0.70,
        "w_ratio": 0.40,
        "h_ratio": 0.12
      }
    },
    "multi_frame": {
      "wave_frames": 5,
      "resource_frames": 3,
      "slot_state_frames": 3
    }
  },
  "traps": [
    {
      "trap_id": "slow_trap",
      "trap_name": "减速陷阱",
      "select_key": "1",
      "upgrade_key": "1",
      "upgrade_hold_ms": 4000,
      "cost": 500,
      "upgrade_cost": 1000,
      "max_level": 3,
      "upgrade_mode": "all_same_type"
    },
    {
      "trap_id": "damage_trap",
      "trap_name": "输出陷阱",
      "select_key": "2",
      "upgrade_key": "2",
      "upgrade_hold_ms": 4000,
      "cost": 800,
      "upgrade_cost": 1500,
      "max_level": 3,
      "upgrade_mode": "all_same_type"
    }
  ],
  "regions": [
    {
      "region_id": "origin",
      "name": "初始视野",
      "description": "按 O 打开地图后的默认视野",
      "enter_actions": []
    },
    {
      "region_id": "entrance_left",
      "name": "左入口区域",
      "description": "左侧入口布防区",
      "enter_actions": [
        {
          "type": "pan_map",
          "direction": "left",
          "distance_ratio": 0.3,
          "duration_ms": 600,
          "repeat": 1
        }
      ]
    }
  ],
  "slots": [
    {
      "slot_id": "A01",
      "name": "左入口减速位1",
      "region_id": "entrance_left",
      "position": {
        "x_ratio": 0.452,
        "y_ratio": 0.561
      },
      "precision": {
        "click_tolerance_px": 6,
        "allow_micro_adjust": true,
        "micro_adjust_pattern": "cross_5_points",
        "micro_adjust_step_px": 4
      },
      "slot_type": "ground",
      "default_trap": "slow_trap",
      "verify": {
        "empty_method": "template_or_color",
        "occupied_method": "image_change",
        "level_method": "level_badge",
        "check_area": {
          "x_ratio": 0.435,
          "y_ratio": 0.545,
          "w_ratio": 0.035,
          "h_ratio": 0.035
        }
      }
    }
  ],
  "waves": [
    {
      "wave": 1,
      "name": "第1波初始布防",
      "execute_once": true,
      "trigger": {
        "type": "wave_eq",
        "value": 1
      },
      "actions": [
        {
          "type": "pan_to_region",
          "region_id": "entrance_left",
          "retry": {
            "max_count": 2,
            "reset_view_before_retry": true
          }
        },
        {
          "type": "place_trap",
          "name": "放置左入口减速",
          "trap_id": "slow_trap",
          "slot_id": "A01",
          "conditions": {
            "resource_gte": 500,
            "slot_empty": "A01"
          },
          "on_condition_failed": {
            "policy": "wait",
            "timeout_ms": 30000,
            "then": "retry_condition"
          },
          "verify": {
            "type": "slot_has_trap",
            "slot_id": "A01",
            "trap_id": "slow_trap",
            "required": true
          },
          "retry": {
            "max_count": 3,
            "interval_ms": 800,
            "reset_view_before_retry": true,
            "micro_adjust_on_retry": true
          },
          "on_fail": {
            "policy": "skip"
          }
        }
      ]
    },
    {
      "wave": 2,
      "name": "第2波升级输出陷阱",
      "execute_once": true,
      "trigger": {
        "type": "wave_eq",
        "value": 2
      },
      "actions": [
        {
          "type": "upgrade_trap",
          "name": "升级输出陷阱到2级",
          "trap_id": "damage_trap",
          "target_level": 2,
          "conditions": {
            "resource_gte": 1500,
            "trap_level_lt": {
              "trap_id": "damage_trap",
              "level": 2
            }
          },
          "on_condition_failed": {
            "policy": "wait",
            "timeout_ms": 30000,
            "then": "retry_condition"
          },
          "execute": {
            "method": "hold_key",
            "key": "2",
            "hold_ms": 4000
          },
          "verify": {
            "type": "trap_level_gte",
            "trap_id": "damage_trap",
            "level": 2,
            "required": false
          },
          "retry": {
            "max_count": 2,
            "interval_ms": 1000
          },
          "on_fail": {
            "policy": "skip"
          }
        }
      ]
    }
  ],
  "boss_reserved": {
    "enabled": false,
    "description": "当前版本不处理 BOSS 专项逻辑，仅预留"
  },
  "metadata": {
    "author": "",
    "created_at": "",
    "updated_at": "",
    "description": "空间站普通难度基础通关脚本"
  }
}
```

---

## 10. 并行开发建议

### 10.1 地图配置器团队优先级

1. JSON 数据模型；
2. 基础信息页；
3. 陷阱配置页；
4. region 配置页；
5. slot 配置页；
6. wave actions 配置页；
7. JSON 导出；
8. JSON Schema 校验。

### 10.2 自动化执行器团队优先级

1. JSON 加载与校验；
2. 游戏窗口识别；
3. OCR 识别波次、资源；
4. 地图界面判断；
5. 按 O 打开地图；
6. 回 origin；
7. pan_to_region；
8. place_trap；
9. upgrade_trap；
10. 条件引擎；
11. retry 机制；
12. 单局日志；
13. 批量跑固定脚本。

---

## 11. V1.0 结论

V1.0 版本冻结以下核心设计：

- 地图配置器与执行器分离；
- 两者只通过 JSON 通信；
- 一个地图一个难度一份脚本；
- 脚本只描述波次内业务动作；
- 执行器负责通用流程；
- 坐标模式使用 `region_screen_ratio`；
- region 通过显式拖拽进入；
- slot 使用 region 内屏幕比例坐标；
- 放置、升级、拆除均支持条件；
- 资源不足默认等待；
- 动作按顺序执行；
- 重试时可回原点；
- 升级按陷阱类型整体升级；
- BOSS 专项逻辑预留。
