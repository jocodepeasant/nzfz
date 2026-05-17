# Tasks

- [x] Task 1: 实现数据类和核心工具函数
  - [x] 1.1: 定义 DetectorConfig 数据类（match_threshold, multi_frame_count, multi_frame_interval_ms），含默认值
  - [x] 1.2: 实现 `crop_roi(frame, roi)` 函数：按 ROI 比例坐标裁剪子图，含边界 clamp
  - [x] 1.3: 实现 `_load_template(template_path)` 内部函数：加载模板图片，文件不存在时返回 None 并打印 warning
  - [x] 1.4: 实现 `_match_single(frame, template, threshold)` 内部函数：执行单次 cv2.matchTemplate，返回 bool
- [x] Task 2: 实现 VisionDetector 类核心逻辑
  - [x] 2.1: 实现 `__init__` 接收 DetectorConfig，检测 OpenCV 可用性
  - [x] 2.2: 实现 `match_template` 方法：截图 → 裁剪 ROI → 加载模板 → 单帧/多帧匹配
  - [x] 2.3: 实现 `is_map_ui_open` 方法：从 rois 取 map_ui_indicator → 调用 match_template
  - [x] 2.4: 实现 `is_slot_empty` 方法：从 slot_verify 取 check_area → 调用 match_template（empty_method）
  - [x] 2.5: 实现 `is_slot_occupied` 方法：从 slot_verify 取 check_area → 调用 match_template（occupied_method）
  - [x] 2.6: 实现 `detect_error_tip` 方法：从 rois 取 place_error_tip → 调用 match_template
  - [x] 2.7: 实现多帧投票逻辑：采集 multi_frame_count 帧，超过半数匹配则返回 True
  - [x] 2.8: 实现 OpenCV 不可用时的降级：所有检测方法返回 False 并打印 warning
- [x] Task 3: 更新 vision/__init__.py 导出
  - [x] 3.1: 导出 VisionDetector, DetectorConfig, crop_roi
- [x] Task 4: 编写单元测试
  - [x] 4.1: 测试 DetectorConfig 默认值和自定义配置
  - [x] 4.2: 测试 crop_roi 正常裁剪和边界 clamp
  - [x] 4.3: 测试 VisionDetector 初始化（OpenCV 可用/不可用）
  - [x] 4.4: 测试 match_template：匹配成功、匹配失败、模板不存在
  - [x] 4.5: 测试 is_map_ui_open：地图打开、地图未打开、rois 无 map_ui_indicator
  - [x] 4.6: 测试 is_slot_empty / is_slot_occupied：正常检测、缺少 check_area
  - [x] 4.7: 测试 detect_error_tip：检测到错误、无错误、rois 无 place_error_tip
  - [x] 4.8: 测试多帧投票：多数通过、多数失败、单帧模式
  - [x] 4.9: 测试 OpenCV 不可用时降级

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
