# Tasks

- [x] Task 1: 实现 NavigatorConfig 数据类和拖拽端点计算
  - [x] SubTask 1.1: 定义 `NavigatorConfig` 数据类，包含 `map_close_wait_ms`、`map_open_wait_ms`、`wait_after_pan_ms` 字段
  - [x] SubTask 1.2: 实现 `calculate_pan_endpoints` 函数：根据 direction（left/right/up/down）和 distance_ratio 计算拖拽起止像素坐标，未知方向返回 None 并打印 warning

- [x] Task 2: 实现 go_to_origin 和 execute_pan_action
  - [x] SubTask 2.1: 实现 `go_to_origin`：按 O 关闭地图 → 等待 → 按 O 重新打开 → 等待 → ensure_map_open 验证；捕获 RuntimeError（pynput 不可用）返回 False
  - [x] SubTask 2.2: 实现 `execute_pan_action`：解析 pan_map 动作配置，计算端点，调用 drag 执行拖拽，支持 repeat 重复，每次后等待 wait_after_pan_ms；捕获 RuntimeError 返回 False

- [x] Task 3: 实现 pan_to_region 并更新导出
  - [x] SubTask 3.1: 实现 `pan_to_region`：先 go_to_origin → 查找 region → 按顺序执行 enter_actions；region 不存在返回 False；origin 区域只回 origin 不拖拽
  - [x] SubTask 3.2: 更新 `engine/__init__.py`，新增导出 `go_to_origin`、`pan_to_region`、`execute_pan_action`、`calculate_pan_endpoints`、`NavigatorConfig`

- [x] Task 4: 编写单元测试
  - [x] SubTask 4.1: 测试 NavigatorConfig 数据类实例化和默认值
  - [x] SubTask 4.2: 测试 calculate_pan_endpoints 四个方向计算正确性
  - [x] SubTask 4.3: 测试 calculate_pan_endpoints 未知方向返回 None
  - [x] SubTask 4.4: 测试 go_to_origin 正常流程（关闭→重新打开→验证）
  - [x] SubTask 4.5: 测试 go_to_origin 地图未打开时直接打开
  - [x] SubTask 4.6: 测试 go_to_origin press_key 抛出 RuntimeError 时返回 False
  - [x] SubTask 4.7: 测试 execute_pan_action 单次拖拽和重复拖拽
  - [x] SubTask 4.8: 测试 execute_pan_action drag 抛出 RuntimeError 时返回 False
  - [x] SubTask 4.9: 测试 pan_to_region 正常导航流程
  - [x] SubTask 4.10: 测试 pan_to_region region_id 不存在返回 False
  - [x] SubTask 4.11: 测试 pan_to_region origin 区域只回 origin 不拖拽
  - [x] SubTask 4.12: 测试 pan_to_region go_to_origin 失败时返回 False

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 1, Task 2, Task 3]
