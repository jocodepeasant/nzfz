# T09 - 格子定位 Spec

## Why

自动化执行器需要将脚本 JSON 中的 slot 比例坐标转换为屏幕像素坐标并执行点击操作，这是放置陷阱（P8）、升级陷阱（P9）、拆除陷阱等所有格子操作的基础。没有格子定位功能，T10 动作执行完整流程无法工作。

## What Changes

- 在 `automation-executor/src/td_executor/engine/slot.py` 中实现 `locate_slot`、`get_micro_adjust_points`、`click_slot` 三个函数
- `locate_slot`：根据 slot_id 查找 slot 配置，调用 `ratio_to_pixel` 将比例坐标转换为像素坐标，返回定位信息 dict
- `get_micro_adjust_points`：根据 precision 配置生成微调偏移点列表，支持 `cross_5_points` 模式
- `click_slot`：定位并点击格子，正常模式点击中心点，微调模式每次调用只尝试一个偏移点（通过多次重试覆盖不同偏移点）
- 更新 `engine/__init__.py` 导出新增公共函数
- 新增测试文件 `automation-executor/tests/test_slot.py`

## Impact

- Affected specs: T10（动作执行完整流程依赖 `click_slot` 定位并点击格子）
- Affected code: `automation-executor/src/td_executor/engine/slot.py`（主要修改）、`automation-executor/src/td_executor/engine/__init__.py`（导出更新）
- 新增测试: `automation-executor/tests/test_slot.py`

## ADDED Requirements

### Requirement: 格子定位 locate_slot

系统 SHALL 提供 `locate_slot(slot_id: str, rect: WindowRect, slots: list[dict]) -> dict` 函数，根据 slot_id 解析 slot 配置并返回定位信息。

- 遍历 `slots` 列表，匹配 `slot.get("slot_id") == slot_id`
- 找到 slot 后，从 `slot["position"]` 中提取 `x_ratio` 和 `y_ratio`
- 调用 `ratio_to_pixel(rect.left, rect.top, rect.width, rect.height, x_ratio, y_ratio)` 计算像素坐标
- 返回 dict 包含：`slot_id`, `region_id`, `center_x`, `center_y`, `precision`, `verify`, `slot_type`, `default_trap`
- slot_id 不存在时，打印 warning 日志并返回空 dict `{}`

#### Scenario: 成功定位格子
- **WHEN** 调用 `locate_slot("A01", rect, slots)` 且 slots 中存在 slot_id="A01"
- **THEN** 返回包含 `center_x`、`center_y`（像素坐标）和原始配置的 dict

#### Scenario: slot_id 不存在
- **WHEN** 调用 `locate_slot("X99", rect, slots)` 且 slots 中不存在该 slot_id
- **THEN** 打印 warning 日志，返回空 dict `{}`

#### Scenario: 坐标转换正确
- **WHEN** slot position 为 `{x_ratio: 0.452, y_ratio: 0.561}`，窗口 rect 为 `left=0, top=0, width=1920, height=1080`
- **THEN** `center_x = int(0 + 1920 * 0.452) = 867`，`center_y = int(0 + 1080 * 0.561) = 605`

### Requirement: 微调偏移点生成 get_micro_adjust_points

系统 SHALL 提供 `get_micro_adjust_points(center_x: int, center_y: int, precision: dict) -> list[tuple[int, int]]` 函数，根据微调策略生成备选点击点列表。

- 读取 `precision.get("allow_micro_adjust", False)`，为 False 时返回空列表
- 读取 `precision.get("micro_adjust_pattern", "")` 确定微调模式
- `cross_5_points` 模式：生成 5 个点，顺序为 [中心, 上, 下, 左, 右]，步长为 `precision.get("micro_adjust_step_px", 4)`
  - 中心: `(center_x, center_y)`
  - 上: `(center_x, center_y - step)`
  - 下: `(center_x, center_y + step)`
  - 左: `(center_x - step, center_y)`
  - 右: `(center_x + step, center_y)`
- 未知模式时打印 warning 日志并返回空列表
- precision 为 None 或空 dict 时返回空列表

#### Scenario: cross_5_points 模式
- **WHEN** 调用 `get_micro_adjust_points(867, 605, {"allow_micro_adjust": True, "micro_adjust_pattern": "cross_5_points", "micro_adjust_step_px": 4})`
- **THEN** 返回 `[(867, 605), (867, 601), (867, 609), (863, 605), (871, 605)]`

#### Scenario: 不允许微调
- **WHEN** 调用 `get_micro_adjust_points(867, 605, {"allow_micro_adjust": False})`
- **THEN** 返回空列表 `[]`

#### Scenario: precision 为空
- **WHEN** 调用 `get_micro_adjust_points(867, 605, {})`
- **THEN** 返回空列表 `[]`

#### Scenario: 未知微调模式
- **WHEN** 调用 `get_micro_adjust_points(867, 605, {"allow_micro_adjust": True, "micro_adjust_pattern": "unknown"})`
- **THEN** 打印 warning 日志，返回空列表 `[]`

### Requirement: 格子点击 click_slot

系统 SHALL 提供 `click_slot(slot_id: str, rect: WindowRect, slots: list[dict], micro_adjust: bool = False) -> bool` 函数，定位并点击格子。

- 调用 `locate_slot(slot_id, rect, slots)` 获取定位信息
- 定位失败（返回空 dict）时，返回 False
- **正常模式**（`micro_adjust=False`）：调用 `click_at(center_x, center_y)` 点击中心点，返回 True
- **微调模式**（`micro_adjust=True`）：
  - 调用 `get_micro_adjust_points(center_x, center_y, precision)` 获取偏移点列表
  - 使用模块级内部计数器 `_micro_adjust_index` 记录当前应尝试的偏移点索引
  - 每次调用只点击一个偏移点（索引递增后取模），通过多次重试覆盖不同偏移点
  - 偏移点列表为空时，回退到点击中心点
  - 调用 `click_at` 后返回 True
- `click_at` 抛出异常时（如 pyautogui 不可用），打印 warning 日志并返回 False
- 每次对新的 slot_id 调用时，重置该 slot 的微调索引为 0

#### Scenario: 正常模式点击
- **WHEN** 调用 `click_slot("A01", rect, slots, micro_adjust=False)`
- **THEN** 在 slot 中心点调用 `click_at(center_x, center_y)`，返回 True

#### Scenario: 微调模式第一次调用
- **WHEN** 调用 `click_slot("A01", rect, slots, micro_adjust=True)` 且偏移点列表为 [(867,605), (867,601), (867,609), (863,605), (871,605)]
- **THEN** 点击第 0 个偏移点 (867, 605)，返回 True

#### Scenario: 微调模式第二次调用
- **WHEN** 再次调用 `click_slot("A01", rect, slots, micro_adjust=True)`
- **THEN** 点击第 1 个偏移点 (867, 601)，返回 True

#### Scenario: 微调模式索引循环
- **WHEN** 调用 5 次后再次调用 `click_slot("A01", rect, slots, micro_adjust=True)`
- **THEN** 索引取模回到 0，点击第 0 个偏移点

#### Scenario: slot_id 不存在
- **WHEN** 调用 `click_slot("X99", rect, slots)`
- **THEN** 返回 False

#### Scenario: click_at 抛出异常
- **WHEN** `click_at` 抛出 RuntimeError（pyautogui 不可用）
- **THEN** 打印 warning 日志，返回 False

#### Scenario: 微调模式无偏移点
- **WHEN** 调用 `click_slot("A01", rect, slots, micro_adjust=True)` 且 `get_micro_adjust_points` 返回空列表
- **THEN** 回退到点击中心点，返回 True

### Requirement: 微调索引管理

系统 SHALL 维护一个模块级的微调索引字典 `_micro_adjust_indices: dict[str, int]`，用于跟踪每个 slot_id 的当前微调偏移点索引。

- 键为 `slot_id`，值为当前偏移点索引
- 每次微调模式点击后，索引递增 1 并对偏移点列表长度取模
- 切换到新的 slot_id 时，索引从 0 开始（若该 slot_id 首次出现则自动初始化为 0）
- 正常模式（`micro_adjust=False`）不影响索引

## MODIFIED Requirements

### Requirement: engine 包导出

`td_executor.engine.__init__` SHALL 导出 `locate_slot`, `get_micro_adjust_points`, `click_slot` 函数，供外部模块直接 `from td_executor.engine import ...` 使用。
