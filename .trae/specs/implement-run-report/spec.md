# 单局日志与报告 Spec

## Why
automation-executor 目前 `engine/report.py` 仅有 `raise NotImplementedError` 的桩函数，无法记录任何动作执行结果。单局日志是 P12 优先级需求，是后续动作执行流程（T10）中埋入日志记录点的前置依赖，也是批量执行（T13）生成报告的基础。

## What Changes
- 新增 `ActionLog` 数据类，记录单个动作的执行日志（类型、名称、波次、时间戳、成功与否、重试次数、错误信息）
- 新增 `RunReport` 数据类，记录整局运行报告（脚本信息、起止时间、结果、动作列表、摘要统计）
- 实现 `RunReport.add_action()` 方法，追加动作日志
- 实现 `RunReport.summary()` 方法，返回统计摘要 dict
- 实现 `write_report()` 函数，将 `RunReport` 序列化为 JSON 文件（datetime 使用 ISO 8601 格式）
- 新增 `RunReport.to_dict()` 方法，支持序列化为嵌套 dict

## Impact
- Affected specs: P12（单局日志）
- Affected code:
  - `automation-executor/src/td_executor/engine/report.py`（主要变更）
  - `automation-executor/tests/test_report.py`（新增测试）

## ADDED Requirements

### Requirement: ActionLog 数据类
系统 SHALL 提供 `ActionLog` 数据类，记录单个动作的执行日志。

#### Scenario: 创建动作日志
- **WHEN** 创建 `ActionLog(action_type="place_trap", action_name="放置减速", wave=1, started_at=datetime.now())`
- **THEN** 实例包含指定的 action_type、action_name、wave、started_at，其余字段为默认值

#### Scenario: 记录执行结果
- **WHEN** 动作执行完成后设置 `finished_at`、`success`、`retry_count`、`error_message`
- **THEN** 日志完整记录了该动作的执行生命周期

### Requirement: RunReport 数据类
系统 SHALL 提供 `RunReport` 数据类，记录整局运行报告。

#### Scenario: 创建运行报告
- **WHEN** 创建 `RunReport(script_id="v1", script_name="脚本", started_at=datetime.now())`
- **THEN** 实例包含指定的 script_id、script_name、started_at，其余字段为默认值

#### Scenario: 追加动作日志
- **WHEN** 调用 `report.add_action(log)`
- **THEN** log 被追加到 `report.actions` 列表

#### Scenario: 生成摘要
- **WHEN** 调用 `report.summary()`
- **THEN** 返回包含 total、success、fail、duration_seconds 的 dict

### Requirement: 报告持久化
系统 SHALL 提供将 RunReport 写入 JSON 文件的能力。

#### Scenario: 写入 JSON 文件
- **WHEN** 调用 `write_report(path, report)`
- **THEN** 在 path 指定位置生成合法 JSON 文件
- **AND** datetime 字段序列化为 ISO 8601 字符串
- **AND** ActionLog 嵌套序列化为 dict 列表

#### Scenario: 目录不存在时自动创建
- **WHEN** 调用 `write_report(path, report)` 且 path 的父目录不存在
- **THEN** 自动创建父目录后写入文件
