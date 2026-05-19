# 修复脚本预览 traps 字段 TypeError Spec

## Why

GUI 脚本预览中 `_show_preview` 方法使用 `", ".join(traps)` 拼接陷阱列表，但脚本 JSON 的 `traps` 字段是 dict 列表（含 `trap_id`、`trap_name` 等），不是 str 列表，导致 `TypeError: sequence item 0: expected str instance, dict found`。

## What Changes

- 修改 `script_tab.py` 的 `_show_preview` 方法，从 traps dict 列表中提取 `trap_name`（或 `trap_id`）再拼接

## Impact

- Affected code: `automation-executor/src/td_executor/ui/script_tab.py`（`_show_preview` 方法）

## ADDED Requirements

### Requirement: 兼容 dict 格式的 traps 列表

系统 SHALL 在脚本预览中正确处理 `traps` 字段为 dict 列表的情况。

- 当 `traps` 元素为 dict 时，提取 `trap_name`（优先）或 `trap_id` 作为显示名称
- 当 `traps` 元素为 str 时，保持原有行为
- 空列表时显示"无"

#### Scenario: traps 为 dict 列表
- **WHEN** 脚本 `traps` 字段为 `[{"trap_id": "歼灭者", "trap_name": "歼灭者", ...}]`
- **THEN** 预览中陷阱列表显示"歼灭者"，不崩溃

#### Scenario: traps 为 str 列表
- **WHEN** 脚本 `traps` 字段为 `["歼灭者"]`
- **THEN** 预览中陷阱列表显示"歼灭者"

## MODIFIED Requirements

无

## REMOVED Requirements

无
