# 自动化执行器并行开发任务文档

> 本文档将 P3~P13 及隐含需求拆解为可独立下发、并行开发的任务卡片。
> 同一波次内的任务**修改不同文件、互不依赖**，可分配给不同人员同时编码。

---

## 并行总览

```
✅ T01-屏幕采集 (已完成)
✅ T02-单局日志 (已完成)
✅ T03-重试框架 (已完成)
✅ T04-OCR识别 (已完成)
✅ T05-模板匹配 (已完成)

波次1 (可并行2人):  ~~T02-单局日志~~  |  ~~T03-重试框架~~
                                    ↓
波次2 (可并行2人):  ~~T04-OCR识别~~  |  ~~T05-模板匹配~~
                                    ↓
波次3 (可并行2人):  ~~T06-条件引擎~~  |  ~~T07-按键动作基础~~ ✅
                                    ↓
波次4 (可并行2人):  T08-地图导航  |  ~~T09-格子定位~~ ✅
                                    ↓
波次5 (串行):       T10-动作执行完整流程 → T11-重试集成 → T12-日志集成 → T13-批量执行
```

---

## 通用约定

- **代码风格**：遵循项目现有风格（`from __future__ import annotations`、`logging` 模块、类型注解）
- **依赖安装**：可选依赖通过 `pyproject.toml` 的 `[project.optional-dependencies]` 分组管理，运行时用 `try/except ImportError` 降级
- **脚本 JSON 结构**：参考 `/workspace/schemas/examples/space_station_normal_baseline_v1.json`
- **JSON Schema**：参考 `/workspace/schemas/tower_defense_script_v1.schema.json`
- **设计文档**：参考 `/workspace/tower_defense_automation_design_v1.md`
- **已有可依赖模块**：
  - `td_executor.runtime.window` → `WindowRect`, `find_game_window()`, `focus_window()`, `get_window_rect()`, `is_window_valid()`
  - `td_executor.runtime.capture` → `ScreenCapture`, `CaptureConfig`, `CaptureBackend`
  - `td_executor.runtime.coordinates` → `ratio_to_pixel()`
  - `td_executor.state` → `GameState`
  - `td_executor.script.load` → `load_script_file()`
  - `td_executor.script.validate` → `validate_script_data()`
  - `td_executor.engine.retry` → `RetryManager`, `RetryConfig`, `OnConditionFailedConfig`, `OnFailConfig`, `ActionResult`, `ActionAbortedError`
  - `td_executor.engine.condition` → `ConditionEngine`, `ConditionContext`, `eval_conditions`
  - `td_executor.vision.detector` → `VisionDetector`, `DetectorConfig`, `crop_roi`
  - `td_executor.engine.action` → `press_key`, `click_at`, `drag`, `ensure_map_open`, `execute_action`
  - `td_executor.engine.slot` → `locate_slot`, `get_micro_adjust_points`, `click_slot`

---

## ✅ T01 - 屏幕采集（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/runtime/capture.py` |
| **Spec** | `.trae/specs/implement-screen-capture/` |

### 已实现接口

```python
class CaptureBackend(Enum):
    MSS = "mss"
    DXCAM = "dxcam"

@dataclass
class CaptureConfig:
    backend: CaptureBackend = CaptureBackend.MSS
    region: dict[str, int] | None = None
    output_format: str = "bgr"

class ScreenCapture:
    def __init__(self, config=None, *, backend="mss", region=None, output_format="bgr"): ...
    def start(self) -> None: ...
    def close(self) -> None: ...
    def capture_frame(self) -> np.ndarray: ...  # 返回 BGR ndarray (H, W, 3) uint8
    def __enter__(self) -> ScreenCapture: ...
    def __exit__(self, *_) -> None: ...
```

### 使用方式（供后续任务参考）

```python
from td_executor.runtime.window import WindowRect, find_game_window
from td_executor.runtime.capture import ScreenCapture

rect = find_game_window("逆战")
with ScreenCapture(region={"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height}) as cap:
    frame = cap.capture_frame()  # np.ndarray BGR
```

---

## ✅ T03 - 重试框架（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/engine/retry.py` |
| **Spec** | `.trae/specs/implement-retry-framework/` |

### 已实现接口

```python
class OnConditionFailedPolicy(Enum):
    WAIT = "wait"
    SKIP = "skip"

class OnFailPolicy(Enum):
    SKIP = "skip"
    ABORT = "abort"

@dataclass
class RetryConfig:
    max_count: int = 0
    interval_ms: int = 0
    reset_view_before_retry: bool = False
    micro_adjust_on_retry: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> RetryConfig: ...

@dataclass
class OnConditionFailedConfig:
    policy: OnConditionFailedPolicy = OnConditionFailedPolicy.WAIT
    timeout_ms: int = 30000
    then: str = "retry_condition"

    @classmethod
    def from_dict(cls, d: dict | None) -> OnConditionFailedConfig: ...

@dataclass
class OnFailConfig:
    policy: OnFailPolicy = OnFailPolicy.SKIP

    @classmethod
    def from_dict(cls, d: dict | None) -> OnFailConfig: ...

@dataclass
class ActionResult:
    success: bool
    skipped: bool = False
    attempts: int = 1
    data: Any = None

class ActionAbortedError(Exception): ...

class RetryManager:
    def __init__(self, runtime_defaults: dict | None = None) -> None: ...
    def resolve_retry_config(self, action_retry: dict | None) -> RetryConfig: ...
    def resolve_on_condition_failed(self, action_config: dict | None) -> OnConditionFailedConfig: ...
    def resolve_on_fail(self, action_config: dict | None) -> OnFailConfig: ...
    def wait_for_condition(self, condition_fn: Callable[[], bool], config: OnConditionFailedConfig) -> bool: ...
    def execute_with_retry(
        self,
        action_fn: Callable,
        verify_fn: Callable[[Any], bool],
        retry_config: RetryConfig,
        on_fail_config: OnFailConfig | None = None,
        reset_view_fn: Callable[[], None] | None = None,
        micro_adjust_fn: Callable[[], None] | None = None,
    ) -> ActionResult: ...
```

### 使用方式（供后续任务参考）

```python
from td_executor.engine.retry import RetryManager, RetryConfig, OnFailConfig, ActionAbortedError

rm = RetryManager(runtime_defaults=script["runtime"])
retry_cfg = rm.resolve_retry_config(action.get("retry"))
on_fail_cfg = rm.resolve_on_fail(action.get("on_fail"))

result = rm.execute_with_retry(
    action_fn=lambda: do_place_trap(trap, slot),
    verify_fn=lambda r: verify_slot_occupied(slot),
    retry_config=retry_cfg,
    on_fail_config=on_fail_cfg,
    reset_view_fn=lambda: navigator.go_to_origin(rect, runtime),
    micro_adjust_fn=lambda: slot.click_slot(slot_id, rect, slots, micro_adjust=True),
)
```

---

## 波次 1：无外部依赖，可立即并行

---

### ✅ T02 - 单局日志（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/engine/report.py` |
| **Spec** | `.trae/specs/implement-run-report/` |

#### 需求描述

实现单局运行日志的数据结构定义、收集和持久化功能。日志记录每个动作的执行结果、时间戳、重试次数等信息。

#### 接口定义

```python
"""单局日志与报告。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ActionLog:
    action_type: str
    action_name: str
    wave: int
    started_at: datetime
    finished_at: datetime | None = None
    success: bool | None = None
    retry_count: int = 0
    error_message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunReport:
    script_id: str
    script_name: str
    started_at: datetime
    finished_at: datetime | None = None
    result: str | None = None  # "win" | "lose" | "error" | "timeout"
    total_waves: int = 0
    actions: list[ActionLog] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_action(self, log: ActionLog) -> None: ...
    def summary(self) -> dict[str, Any]: ...


def write_report(path: Path, report: RunReport) -> None:
    """将报告写入 JSON 文件。"""
```

#### 实现要求

1. **数据类**：`ActionLog` 记录单个动作的执行日志，`RunReport` 记录整局运行报告
2. **序列化**：`write_report` 将 `RunReport` 序列化为 JSON 文件，datetime 使用 ISO 8601 格式
3. **摘要**：`RunReport.summary()` 返回统计摘要 dict（总动作数、成功数、失败数、耗时等）
4. **不依赖**：不依赖 OCR、检测器、动作执行等未实现模块，仅定义数据结构和 IO
5. **扩展性**：`extra` 和 `metadata` 字段允许上层灵活附加信息

#### 验收标准

- [x] `ActionLog` 和 `RunReport` 数据类可正常实例化和序列化
- [x] `write_report` 生成合法 JSON 文件，datetime 为 ISO 8601 字符串
- [x] `RunReport.summary()` 返回包含 total/success/fail/duration 的字典
- [x] 不依赖任何未实现模块

---

## 波次 2：依赖 T01（已完成），可立即并行

---

### ✅ T04 - OCR 识别（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/vision/ocr.py` |
| **Spec** | `.trae/specs/implement-ocr-recognition/` |

#### 需求描述

实现 OCR 识别功能，从游戏截图中识别波次数字、资源数字、核心血量等 ROI 区域的文字内容。

#### 接口定义

```python
"""OCR 引擎封装。"""

from __future__ import annotations

import numpy as np
from td_executor.runtime.window import WindowRect
from td_executor.runtime.capture import ScreenCapture


def read_digits_roi(capture: ScreenCapture, rect: WindowRect, roi: dict, keyword: str = "") -> str:
    """从指定 ROI 区域识别数字文本。"""


def read_wave(capture: ScreenCapture, rect: WindowRect, rois: dict, multi_frame: dict | None = None) -> int | None:
    """识别当前波次。多帧投票取众数。"""


def read_resource(capture: ScreenCapture, rect: WindowRect, rois: dict, multi_frame: dict | None = None) -> int | None:
    """识别当前资源数量。多帧投票取众数。"""


def read_core_hp(capture: ScreenCapture, rect: WindowRect, rois: dict, multi_frame: dict | None = None) -> int | None:
    """识别核心血量。"""
```

#### 实现要求

1. **OCR 引擎**：使用 PaddleOCR（`pyproject.toml` 的 `ocr` 可选依赖），通过 `try/except` 处理不可用情况
2. **截图方式**：使用 `ScreenCapture` 实例截取窗口画面，通过 `region` 参数限定窗口区域
3. **ROI 截取**：根据 ROI 的比例坐标和窗口尺寸，计算像素区域后从完整截图中裁剪子图，再送 OCR
4. **数字预处理**：对 ROI 截图做灰度化、二值化、去噪等预处理，提升数字识别准确率
5. **多帧投票**：按 `recognition.multi_frame` 配置采集多帧（如 `wave_frames: 5`），对识别结果取众数，减少误识别
6. **结果清洗**：用正则过滤非数字字符，返回纯数字字符串
7. **降级方案**：PaddleOCR 不可用时，打印 warning 并返回 `None`

#### 验收标准

- [x] `read_digits_roi` 返回纯数字字符串或空字符串
- [x] `read_wave` / `read_resource` / `read_core_hp` 返回 int 或 None
- [x] 多帧投票逻辑正确，至少采集 `multi_frame` 配置的帧数
- [x] PaddleOCR 不可用时优雅降级，不崩溃
- [x] ROI 截图区域与配置的比例坐标一致

---

### ✅ T05 - 模板匹配（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/vision/detector.py` |
| **Spec** | `.trae/specs/implement-vision-detector/` |

#### 已实现接口

```python
@dataclass
class DetectorConfig:
    match_threshold: float = 0.8
    multi_frame_count: int = 3
    multi_frame_interval_ms: int = 100
    templates_dir: str = "assets/templates"

def crop_roi(frame: np.ndarray, roi: dict) -> np.ndarray: ...

class VisionDetector:
    def __init__(self, config: DetectorConfig | None = None) -> None: ...
    def match_template(self, capture, rect, roi, template_path, threshold=None) -> bool: ...
    def is_map_ui_open(self, capture, rect, rois) -> bool: ...
    def is_slot_empty(self, capture, rect, slot_verify) -> bool: ...
    def is_slot_occupied(self, capture, rect, slot_verify) -> bool: ...
    def detect_error_tip(self, capture, rect, rois) -> bool: ...
```

#### 验收标准

- [x] `match_template` 正确执行模板匹配，返回 bool
- [x] `is_map_ui_open` 可判断地图界面状态
- [x] `is_slot_empty` / `is_slot_occupied` 可判断格子占用状态
- [x] 模板图片路径不存在时打印 warning 并返回 `False`，不崩溃
- [x] OpenCV 不可用时优雅降级

---

## 波次 3：依赖波次 2，可并行

---

### ✅ T06 - 条件引擎（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/engine/condition.py` |
| **Spec** | `.trae/specs/implement-condition-engine/` |

#### 需求描述

实现动作执行前的条件判断引擎，解析脚本 JSON 中的 `conditions` 对象，调用 OCR 和检测器获取实时数据，判断条件是否满足。

#### 已实现接口

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from td_executor.runtime.window import WindowRect
from td_executor.runtime.capture import ScreenCapture


@dataclass
class ConditionContext:
    capture: ScreenCapture
    rect: WindowRect
    rois: dict
    slots: list[dict]
    traps: list[dict]
    state: dict | None = None
    multi_frame: dict | None = None


class ConditionEngine:
    def __init__(self, detector=None) -> None: ...
    def eval_conditions(self, conditions: dict[str, Any] | None, ctx: ConditionContext) -> bool: ...


def eval_conditions(
    conditions: dict[str, Any],
    capture: ScreenCapture,
    rect: WindowRect,
    rois: dict,
    slots: list[dict],
    traps: list[dict],
    state: dict[str, Any] | None = None,
) -> bool:
    """评估所有条件，全部满足返回 True。"""
```

#### 条件类型映射

| 条件键 | 含义 | 数据来源 |
|--------|------|---------|
| `resource_gte` | 资源 >= N | OCR `read_resource` |
| `wave_eq` | 波次 == N | OCR `read_wave` |
| `wave_gte` | 波次 >= N | OCR `read_wave` |
| `slot_empty` | 格子为空 | 检测器 `is_slot_empty` |
| `slot_occupied` | 格子已占用 | 检测器 `is_slot_occupied` |
| `trap_level_lt` | 陷阱等级 < N | 状态缓存 |

#### 验收标准

- [x] `eval_conditions` 正确解析所有条件类型
- [x] 短路求值，不满足时立即返回
- [x] OCR 结果在同一轮评估中缓存复用
- [x] 未知条件键不导致崩溃
- [x] 所有条件为空 dict 时返回 `True`

#### engine/__init__.py 新增导出

```python
from td_executor.engine.condition import ConditionContext, ConditionEngine

__all__ = [
    # ... 原有导出 ...
    "ConditionContext",
    "ConditionEngine",
]
```

---

### ✅ T07 - 按键动作基础（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/engine/action.py` |
| **依赖** | T05（检测器判断地图界面状态） |
| **Spec** | `.trae/specs/implement-key-action-basics/` |

#### 已实现接口

```python
def press_key(key: str, hold_ms: int = 0) -> None: ...
def click_at(x: int, y: int, button: str = "left") -> None: ...
def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration_ms: int = 600) -> None: ...
def ensure_map_open(capture: Any, rect: Any, rois: dict) -> bool: ...
def execute_action(action: dict, context: dict) -> dict: ...
```

#### 验收标准

- [x] `press_key` 可模拟按键点击和长按
- [x] `click_at` 可在指定坐标点击
- [x] `drag` 可模拟拖拽操作
- [x] `ensure_map_open` 正确判断地图界面状态并按 O 打开
- [x] `execute_action` 对 `type="log"` 正确处理
- [x] pynput/pyautogui 不可用时优雅降级

---

## 波次 4：依赖波次 3，可并行

---

### T08 - 地图导航

| 项目 | 内容 |
|------|------|
| **优先级** | P6/P7，高 |
| **修改文件** | `automation-executor/src/td_executor/engine/navigator.py` |
| **依赖** | T07（action.py 的 drag 和 ensure_map_open） |
| **与其他任务冲突** | 无，独立文件 |

#### 接口定义

```python
"""地图区域拖拽导航。"""

from __future__ import annotations

from typing import Any

from td_executor.runtime.window import WindowRect


def go_to_origin(rect: WindowRect, runtime: dict) -> bool:
    """回到地图初始视野（关闭地图再重新打开）。"""


def pan_to_region(region_id: str, rect: WindowRect, regions: list[dict], runtime: dict) -> bool:
    """导航到指定区域。"""
```

#### 验收标准

- [ ] `go_to_origin` 正确执行关闭→重新打开地图流程
- [ ] `pan_to_region` 先回 origin 再执行 enter_actions
- [ ] 拖拽方向和距离计算正确
- [ ] `repeat` 重复拖拽正确执行
- [ ] 每次拖拽后等待 `wait_after_pan_ms`

---

### ✅ T09 - 格子定位（已完成）

| 项目 | 内容 |
|------|------|
| **状态** | ✅ 已完成 |
| **修改文件** | `automation-executor/src/td_executor/engine/slot.py` |
| **依赖** | `coordinates.py`（已实现） |
| **Spec** | `.trae/specs/implement-slot-positioning/` |

#### 已实现接口

```python
def locate_slot(slot_id: str, rect: WindowRect, slots: list[dict]) -> dict: ...
def get_micro_adjust_points(center_x: int, center_y: int, precision: dict | None) -> list[tuple[int, int]]: ...
def click_slot(slot_id: str, rect: WindowRect, slots: list[dict], micro_adjust: bool = False) -> bool: ...
```

#### 验收标准

- [x] `locate_slot` 正确将比例坐标转换为屏幕像素坐标
- [x] `get_micro_adjust_points` 生成正确的偏移点列表（cross_5_points 模式）
- [x] `click_slot` 在中心点点击，微调模式每次调用只尝试一个偏移点
- [x] slot_id 不存在时返回空 dict 或打印 warning

---

## 波次 5：串行集成

---

### T10 - 动作执行完整流程

| 项目 | 内容 |
|------|------|
| **优先级** | P8/P9，高 |
| **修改文件** | `automation-executor/src/td_executor/engine/action.py` |
| **依赖** | T06（条件引擎）、T07（按键基础）、T08（导航）、T09（格子定位） |

#### 验收标准

- [ ] `execute_action` 支持 `place_trap`、`upgrade_trap`、`remove_trap`、`pan_to_region`、`log` 五种 action type
- [ ] 每种动作按流程正确执行
- [ ] 条件不满足时按 `on_condition_failed.policy` 处理
- [ ] 动作失败时按 `retry` 配置重试
- [ ] 重试耗尽后按 `on_fail.policy` 处理

---

### T11 - 重试集成

| 项目 | 内容 |
|------|------|
| **优先级** | P11，中 |
| **修改文件** | `automation-executor/src/td_executor/engine/retry.py` |
| **依赖** | T08（导航，用于 `reset_view_before_retry`）、T10（动作执行） |

#### 验收标准

- [ ] `reset_view_before_retry=True` 时重试前正确重置视野
- [ ] `micro_adjust_on_retry=True` 时重试使用微调点击
- [ ] RetryManager 与动作执行正确集成

---

### T12 - 日志集成

| 项目 | 内容 |
|------|------|
| **优先级** | P12，中 |
| **修改文件** | `automation-executor/src/td_executor/engine/report.py`、`automation-executor/src/td_executor/engine/action.py` |
| **依赖** | T02（日志数据结构）、T10（动作执行） |

#### 验收标准

- [ ] 每个动作执行都有对应的 `ActionLog` 记录
- [ ] 对局结束生成完整 `RunReport` 并写入文件
- [ ] 日志不影响动作执行的性能

---

### T13 - 批量执行

| 项目 | 内容 |
|------|------|
| **优先级** | P13，低 |
| **修改文件** | `automation-executor/src/td_executor/engine/batch.py`、`automation-executor/src/td_executor/cli.py` |
| **依赖** | T10~T12（完整单局流程） |

#### 验收标准

- [ ] `run_single` 可执行完整的单局流程
- [ ] 主循环正确识别波次并执行对应动作
- [ ] 超时、胜利、失败状态正确处理
- [ ] `run_batch` 顺序执行多个脚本
- [ ] CLI `run` 命令可触发完整执行流程

---

## 附录：文件修改矩阵

| 任务 | capture.py | ocr.py | detector.py | action.py | condition.py | navigator.py | slot.py | retry.py | report.py | batch.py | cli.py | state.py |
|------|:---------:|:------:|:-----------:|:---------:|:------------:|:------------:|:-------:|:--------:|:---------:|:--------:|:------:|:--------:|
| T01  | ✅ | | | | | | | | | | | |
| T02  | | | | | | | | | ✅ | | | |
| T03  | | | | | | | | ✅ | | | | |
| T04  | | ✅ | | | | | | | | | | |
| T05  | | | ✅ | | | | | | | | | |
| T06  | | | | | ✅ | | | | | | | |
| T07  | | | | ✅ | | | | | | | | |
| T08  | | | | | | ✏️ | | | | | | |
| T09  | | | | | | | ✅ | | | | | |
| T10  | | | | ✏️ | | | | | | | | |
| T11  | | | | | | | | ✏️ | | | | |
| T12  | | | | ✏️ | | | | | ✏️ | | | |
| T13  | | | | | | | | | | ✏️ | ✏️ | |

> ✅ = 已完成 | ✏️ = 待修改文件。同一波次内的任务修改不同文件，无冲突。

---

## 附录：实现进度追踪

| 编号 | 需求 | 对应代码 | 状态 |
|------|------|---------|------|
| P1 | JSON 加载与校验 | `script/load.py` + `script/validate.py` | ✅ 已实现 |
| P2 | 游戏窗口识别 | `runtime/window.py` | ✅ 已实现 |
| — | 屏幕采集 | `runtime/capture.py` | ✅ 已实现 (T01) |
| P3 | OCR 识别波次、资源 | `vision/ocr.py` | ✅ 已实现 (T04) |
| P4 | 地图界面判断 | `vision/detector.py` | ✅ 已实现 (T05) |
| P5 | 按 O 打开地图 | `engine/action.py` | ✅ 已实现 (T07) |
| P6 | 回 origin | `engine/navigator.py` | ❌ T08 |
| P7 | pan_to_region | `engine/navigator.py` | ❌ T08 |
| P8 | place_trap | `engine/action.py` + `engine/slot.py` | ✅ slot.py 已实现 (T09)，T10 待完成 |
| P9 | upgrade_trap | `engine/action.py` | ❌ T10 |
| P10 | 条件引擎 | `engine/condition.py` | ✅ 已实现 (T06) |
| P11 | retry 机制 | `engine/retry.py` | ✅ 已实现 (T03)，T11 集成待完成 |
| P12 | 单局日志 | `engine/report.py` | ✅ 已实现 (T02) |
| P13 | 批量跑固定脚本 | `engine/batch.py` | ❌ T13 |
