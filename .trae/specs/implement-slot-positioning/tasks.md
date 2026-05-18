# Tasks

- [x] Task 1: 实现 locate_slot 格子定位函数
  - [x] SubTask 1.1: 实现 slot_id 查找逻辑，遍历 slots 列表匹配 slot_id
  - [x] SubTask 1.2: 调用 ratio_to_pixel 将 position.x_ratio/y_ratio 转换为像素坐标
  - [x] SubTask 1.3: 构建并返回定位信息 dict（slot_id, region_id, center_x, center_y, precision, verify, slot_type, default_trap）
  - [x] SubTask 1.4: slot_id 不存在时打印 warning 并返回空 dict

- [x] Task 2: 实现 get_micro_adjust_points 微调偏移点生成函数
  - [x] SubTask 2.1: 读取 precision 配置，allow_micro_adjust 为 False 时返回空列表
  - [x] SubTask 2.2: 实现 cross_5_points 模式：中心 + 上下左右，步长为 micro_adjust_step_px
  - [x] SubTask 2.3: 未知模式时打印 warning 并返回空列表
  - [x] SubTask 2.4: precision 为 None 或空 dict 时返回空列表

- [x] Task 3: 实现 click_slot 格子点击函数
  - [x] SubTask 3.1: 调用 locate_slot 获取定位信息，失败返回 False
  - [x] SubTask 3.2: 正常模式调用 click_at(center_x, center_y)，返回 True
  - [x] SubTask 3.3: 微调模式使用 _micro_adjust_indices 索引，每次调用只点击一个偏移点
  - [x] SubTask 3.4: 微调索引递增并取模，切换 slot_id 时从 0 开始
  - [x] SubTask 3.5: 偏移点列表为空时回退到点击中心点
  - [x] SubTask 3.6: click_at 抛出异常时打印 warning 并返回 False

- [x] Task 4: 更新 engine/__init__.py 导出
  - [x] SubTask 4.1: 添加 locate_slot, get_micro_adjust_points, click_slot 的导入和导出

- [x] Task 5: 编写测试 test_slot.py
  - [x] SubTask 5.1: 测试 locate_slot 成功定位/slot_id 不存在/坐标转换正确
  - [x] SubTask 5.2: 测试 get_micro_adjust_points cross_5_points/不允许微调/空 precision/未知模式
  - [x] SubTask 5.3: 测试 click_slot 正常模式/微调模式/索引循环/slot 不存在/异常处理/无偏移点回退

# Task Dependencies

- Task 2 无外部依赖，可与 Task 1 并行
- Task 3 依赖 Task 1 和 Task 2（click_slot 调用 locate_slot 和 get_micro_adjust_points）
- Task 4 依赖 Task 1~3（需要所有函数实现完成）
- Task 5 依赖 Task 1~4（需要所有函数实现完成）
