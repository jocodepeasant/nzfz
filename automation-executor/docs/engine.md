# Engine 模块 — 执行引擎

执行引擎是 automation-executor 的核心模块，负责动作执行、条件判断、失败重试、地图导航、格子定位和报告生成。

## 模块结构

```
engine/
├── __init__.py      # 模块导出
├── action.py        # 动作执行器
├── batch.py         # 批量执行（占位）
├── boss.py          # BOSS 专项逻辑（占位）
├── condition.py     # 条件判断引擎
├── navigator.py     # 地图区域拖拽导航
├── report.py        # 单局日志与报告
├── retry.py         # 失败重试策略
└── slot.py          # 陷阱格子定位与点击
```

---

## action.py — 动作执行器

### 概述

动作执行器是引擎的核心调度中心，负责解析动作类型并分发到对应的执行逻辑。支持的动作类型包括：

| 动作类型 | 说明 |
|---------|------|
| `place_trap` | 放置陷阱 |
| `upgrade_trap` | 升级陷阱 |
| `remove_trap` | 拆除陷阱 |
| `pan_to_region` | 导航到地图区域 |
| `log` | 日志输出 |

### 核心类与函数

#### `ActionExecutor`

动作执行器主类，协调条件检查、重试策略和视觉验证。

```python
class ActionExecutor:
    def __init__(self, runtime_defaults: dict | None = None, detector: Any | None = None)
    def execute(self, action: dict, context: dict) -> dict
```

**初始化参数：**
- `runtime_defaults` — 运行时默认配置，用于重试策略的默认值
- `detector` — 视觉检测器实例，默认创建 `VisionDetector`

**`execute()` 返回值：**
```python
{
    "success": bool,     # 是否成功
    "skipped": bool,     # 是否跳过
    "attempts": int,     # 尝试次数
    "error": str | None  # 错误信息
}
```

**执行流程（以 `place_trap` 为例）：**
1. 确保地图 UI 已打开（`ensure_map_open`）
2. 定位格子坐标（`locate_slot`）
3. 导航到目标区域（`pan_to_region`）
4. 检查前置条件（`_check_conditions`）
5. 查找陷阱配置
6. 构建验证函数（`_build_verify_fn`）
7. 带重试执行动作（`execute_with_retry`）
8. 更新陷阱等级状态

#### `press_key(key, hold_ms=0, overlay=None, hwnd=0)`

按键操作。优先使用 Win32 `PostMessage`（通过 `hwnd`），降级到 `pynput`。

#### `click_at(x, y, button="left", overlay=None, hwnd=0, ...)`

点击操作。优先使用 Win32 `PostMessage`，降级到 `pyautogui`。

#### `drag(from_x, from_y, to_x, to_y, duration_ms=600)`

拖拽操作，基于 `pyautogui` 实现。

#### `ensure_map_open(capture, rect, rois, context=None) -> bool`

确保地图 UI 已打开。通过视觉检测判断地图状态，若未打开则按 `O` 键尝试打开，最多重试 3 次（每次等待 800ms）。

#### `execute_action(action, context) -> dict`

模块级便捷函数，创建默认 `ActionExecutor` 并执行动作。

### 条件验证函数（`_build_verify_fn`）

| 验证类型 | 说明 |
|---------|------|
| `slot_has_trap` | 验证格子是否已放置陷阱 |
| `slot_empty` | 验证格子是否为空 |
| `trap_level_gte` | 验证陷阱等级是否达到指定值 |

---

## condition.py — 条件判断引擎

### 概述

条件引擎负责在动作执行前进行前置条件判断，支持资源、波次、格子状态和陷阱等级等条件类型。采用短路求值策略，任一条件不满足即返回 `False`。

### 核心类

#### `ConditionContext`

条件求值上下文，封装条件判断所需的全部运行时数据。

```python
@dataclass
class ConditionContext:
    capture: ScreenCapture    # 屏幕截图器
    rect: WindowRect          # 窗口矩形
    rois: dict                # ROI 区域定义
    slots: list[dict]         # 格子配置列表
    traps: list[dict]         # 陷阱配置列表
    state: dict | None = None       # 对局状态
    multi_frame: dict | None = None # 多帧采集配置
```

#### `ConditionEngine`

条件引擎，根据条件字典进行短路求值。内部缓存资源/波次的 OCR 结果，避免重复识别。

```python
class ConditionEngine:
    def __init__(self, detector: VisionDetector | None = None)
    def eval_conditions(self, conditions: dict, ctx: ConditionContext) -> bool
```

### 支持的条件类型

| 条件键 | 值类型 | 说明 |
|-------|--------|------|
| `resource_gte` | `int` | 当前资源 ≥ 指定值 |
| `wave_eq` | `int` | 当前波次 = 指定值 |
| `wave_gte` | `int` | 当前波次 ≥ 指定值 |
| `slot_empty` | `str` (slot_id) | 指定格子为空 |
| `slot_occupied` | `str` (slot_id) | 指定格子已占用 |
| `trap_level_lt` | `dict` | 陷阱等级 < 指定值 |

**`trap_level_lt` 值格式：**
```json
{"trap_id": "trap_1", "level": 3}
```

### 模块级函数

#### `eval_conditions(conditions, capture, rect, rois, slots, traps, state=None) -> bool`

便捷函数，自动创建 `ConditionEngine` 和 `ConditionContext` 并求值。

---

## navigator.py — 地图区域拖拽导航

### 概述

导航模块负责在游戏地图上通过拖拽操作将视角移动到目标区域。采用"先回原点再拖拽"的策略确保导航一致性。

### 核心类

#### `NavigatorConfig`

导航配置数据类。

```python
@dataclass
class NavigatorConfig:
    map_close_wait_ms: int = 500     # 关闭地图后等待时间
    map_open_wait_ms: int = 800      # 打开地图后等待时间
    wait_after_pan_ms: int = 800     # 拖拽后等待时间
```

### 核心函数

#### `calculate_pan_endpoints(rect, direction, distance_ratio) -> tuple | None`

根据窗口矩形、方向和距离比例计算拖拽起止坐标。

**方向：** `left` / `right` / `up` / `down`

**计算逻辑：** 起点为窗口中心，终点根据方向和距离比例偏移。

#### `go_to_origin(capture, rect, rois, runtime, config=None) -> bool`

将视角回到地图原点。策略：若地图已打开，先关闭再重新打开，确保视角重置。

#### `execute_pan_action(action, rect, config=None) -> bool`

执行单次拖拽动作。支持 `repeat` 字段重复拖拽。

**动作配置字段：**
- `direction` — 拖拽方向
- `distance_ratio` — 距离比例
- `duration_ms` — 拖拽持续时间（默认 600ms）
- `repeat` — 重复次数（默认 1）

#### `pan_to_region(region_id, rect, regions, capture, rois, runtime, config=None) -> bool`

导航到指定区域。先回到原点，再按区域的 `enter_actions` 依次执行拖拽。

---

## retry.py — 失败重试策略

### 概述

重试模块提供灵活的失败处理机制，支持动作重试、条件等待和失败降级策略。

### 枚举类型

#### `OnConditionFailedPolicy`

条件不满足时的策略：
- `WAIT` — 等待条件满足
- `SKIP` — 跳过当前动作

#### `OnFailPolicy`

动作失败后的策略：
- `SKIP` — 跳过，继续执行后续动作
- `ABORT` — 中止整个脚本执行

### 数据类

#### `RetryConfig`

重试配置。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `max_count` | `int` | `0` | 最大重试次数 |
| `interval_ms` | `int` | `0` | 重试间隔（毫秒） |
| `reset_view_before_retry` | `bool` | `False` | 重试前重置视角 |
| `micro_adjust_on_retry` | `bool` | `False` | 重试时微调点击位置 |

#### `OnConditionFailedConfig`

条件不满足时的处理配置。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `policy` | `OnConditionFailedPolicy` | `WAIT` | 等待策略 |
| `timeout_ms` | `int` | `30000` | 等待超时（毫秒） |
| `then` | `str` | `"retry_condition"` | 超时后的后续动作 |

#### `OnFailConfig`

动作失败后的处理配置。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `policy` | `OnFailPolicy` | `SKIP` | 失败策略 |

#### `ActionResult`

动作执行结果。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `success` | `bool` | — | 是否成功 |
| `skipped` | `bool` | `False` | 是否跳过 |
| `attempts` | `int` | `1` | 尝试次数 |
| `data` | `Any` | `None` | 附加数据 |

### 核心类

#### `RetryManager`

重试管理器，负责解析重试配置和执行带重试的动作。

```python
class RetryManager:
    def __init__(self, runtime_defaults: dict | None = None)

    def resolve_retry_config(self, action_retry: dict | None) -> RetryConfig
    def resolve_on_condition_failed(self, action_config: dict | None) -> OnConditionFailedConfig
    def resolve_on_fail(self, action_config: dict | None) -> OnFailConfig
    def wait_for_condition(self, condition_fn, config) -> bool
    def execute_with_retry(self, action_fn, verify_fn, retry_config, ...) -> ActionResult
```

**`execute_with_retry` 执行流程：**
1. 总尝试次数 = `max_count + 1`
2. 每次重试前：可选重置视角、微调点击位置、等待间隔
3. 执行动作函数，若抛异常则继续重试
4. 调用验证函数检查结果
5. 验证通过则返回成功
6. 全部失败后按 `OnFailConfig` 决定跳过或抛出 `ActionAbortedError`

### 异常类

#### `ActionAbortedError`

当 `OnFailPolicy.ABORT` 且动作全部失败时抛出。

---

## slot.py — 陷阱格子定位与点击

### 概述

格子模块负责将脚本中的逻辑格子 ID 转换为屏幕像素坐标，并执行点击操作。支持微调点击模式，在重试时尝试偏移位置以提高成功率。

### 核心函数

#### `locate_slot(slot_id, rect, slots) -> dict`

根据 `slot_id` 查找格子配置，通过比例坐标转换为像素坐标。

**返回值：**
```python
{
    "slot_id": str,
    "region_id": str,
    "center_x": int,
    "center_y": int,
    "precision": dict,
    "verify": dict,
    "slot_type": str,
    "default_trap": str,
}
```

#### `get_micro_adjust_points(center_x, center_y, precision) -> list[tuple[int, int]]`

生成微调点击点列表。当前支持 `cross_5_points` 模式（十字形 5 个点：中心 + 上下左右各偏移一步）。

**配置字段：**
- `allow_micro_adjust` — 是否启用微调
- `micro_adjust_pattern` — 微调模式（如 `cross_5_points`）
- `micro_adjust_step_px` — 微调步长（默认 4px）

#### `click_slot(slot_id, rect, slots, micro_adjust=False, overlay=None, hwnd=0, game_hwnd=0) -> bool`

点击指定格子。启用微调模式时，按轮转顺序选择偏移点。

---

## report.py — 单局日志与报告

### 概述

报告模块负责记录每次脚本执行的动作日志和运行统计，并持久化为 JSON 文件。

### 核心类

#### `ActionLog`

单条动作日志记录。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `action_type` | `str` | 动作类型 |
| `action_name` | `str` | 动作名称 |
| `wave` | `int` | 所属波次 |
| `started_at` | `datetime` | 开始时间 |
| `finished_at` | `datetime \| None` | 结束时间 |
| `success` | `bool \| None` | 是否成功 |
| `retry_count` | `int` | 重试次数 |
| `error_message` | `str \| None` | 错误信息 |
| `extra` | `dict` | 附加数据 |

#### `RunReport`

单次运行报告。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `script_id` | `str` | 脚本 ID |
| `script_name` | `str` | 脚本名称 |
| `started_at` | `datetime` | 开始时间 |
| `finished_at` | `datetime \| None` | 结束时间 |
| `result` | `str \| None` | 运行结果（`completed` / `stopped`） |
| `total_waves` | `int` | 总波次数 |
| `actions` | `list[ActionLog]` | 动作日志列表 |
| `metadata` | `dict` | 元数据 |

**`summary()` 运行统计：**
```python
{
    "total": int,           # 总动作数
    "success": int,         # 成功数
    "fail": int,            # 失败数
    "duration_seconds": float | None  # 运行时长
}
```

#### `write_report(path, report)`

将报告写入 JSON 文件，自动创建父目录。

---

## batch.py — 批量执行（占位）

批量跑固定脚本，当前为占位实现，调用 `run_batch()` 会抛出 `NotImplementedError`。

---

## boss.py — BOSS 专项逻辑（占位）

BOSS 预留逻辑，当前 `handle_boss_reserved()` 为空实现。
