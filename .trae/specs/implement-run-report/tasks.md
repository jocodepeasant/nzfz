# Tasks

- [x] Task 1: 实现 ActionLog 和 RunReport 数据类
  - [x] 1.1: 定义 `ActionLog` dataclass（action_type, action_name, wave, started_at, finished_at, success, retry_count, error_message, extra）
  - [x] 1.2: 定义 `RunReport` dataclass（script_id, script_name, started_at, finished_at, result, total_waves, actions, metadata）
  - [x] 1.3: 实现 `RunReport.add_action(log)` 方法
  - [x] 1.4: 实现 `RunReport.summary()` 方法，返回 total/success/fail/duration_seconds
  - [x] 1.5: 实现 `RunReport.to_dict()` 方法，递归序列化为嵌套 dict（datetime 转 ISO 8601 字符串）
  - [x] 1.6: 实现 `ActionLog.to_dict()` 方法
- [x] Task 2: 实现 write_report 函数
  - [x] 2.1: 实现 `write_report(path, report)` 函数，将 RunReport 序列化为 JSON 文件
  - [x] 2.2: 父目录不存在时自动创建
- [x] Task 3: 编写单元测试
  - [x] 3.1: 测试 ActionLog 创建和默认值
  - [x] 3.2: 测试 RunReport 创建和默认值
  - [x] 3.3: 测试 add_action 追加日志
  - [x] 3.4: 测试 summary 返回正确的统计信息
  - [x] 3.5: 测试 to_dict 序列化（datetime 为 ISO 8601 字符串）
  - [x] 3.6: 测试 write_report 生成合法 JSON 文件
  - [x] 3.7: 测试 write_report 自动创建父目录

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1] and [Task 2]
