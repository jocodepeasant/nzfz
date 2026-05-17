# 模板匹配检测器 (Vision Detector) Spec

## Why
automation-executor 需要通过图像识别判断游戏界面状态（地图是否打开、格子是否为空/已占用、是否出现错误提示等），当前 `vision/detector.py` 仅为 `raise NotImplementedError` 的占位函数，导致条件引擎（T06）和动作执行（T07/T10）无法获取视觉反馈，是视觉管线的关键缺失环节。

## What Changes
- 将 `vision/detector.py` 从占位实现替换为基于 OpenCV 模板匹配的完整检测器
- 新增 `VisionDetector` 类，封装截图裁剪、模板匹配、多帧投票等核心能力
- 新增 `DetectorConfig` 数据类，配置匹配阈值、多帧投票参数
- 实现 `match_template` 通用模板匹配函数
- 实现 `is_map_ui_open` 判断地图界面状态
- 实现 `is_slot_empty` / `is_slot_occupied` 判断格子占用状态
- 实现 `detect_error_tip` 检测放置错误提示
- 更新 `vision/__init__.py` 导出新增的公开类型
- OpenCV 不可用时优雅降级，打印 warning 并返回安全默认值

## Impact
- Affected specs: T06（条件引擎）的前置依赖，T07/T10（动作执行）的协作方
- Affected code:
  - `automation-executor/src/td_executor/vision/detector.py`（主要修改）
  - `automation-executor/src/td_executor/vision/__init__.py`（导出更新）

## ADDED Requirements

### Requirement: DetectorConfig 数据类
系统 SHALL 提供 `DetectorConfig` 数据类，封装检测器配置参数。

#### Scenario: 默认配置
- **WHEN** 创建 `DetectorConfig()` 不传参数
- **THEN** match_threshold 为 0.8，multi_frame_count 为 3，multi_frame_interval_ms 为 100

#### Scenario: 自定义配置
- **WHEN** 创建 `DetectorConfig(match_threshold=0.9, multi_frame_count=5)`
- **THEN** match_threshold 为 0.9，multi_frame_count 为 5

### Requirement: VisionDetector 类
系统 SHALL 提供 `VisionDetector` 类，封装截图裁剪、模板匹配、多帧投票等核心能力。

#### Scenario: 初始化
- **WHEN** 创建 `VisionDetector(config=DetectorConfig())`
- **THEN** VisionDetector 持有配置，可用于后续检测

#### Scenario: OpenCV 不可用时初始化
- **WHEN** 创建 `VisionDetector()` 且 opencv-python-headless 未安装
- **THEN** 不抛异常，但后续检测方法返回安全默认值并打印 warning

### Requirement: ROI 裁剪
系统 SHALL 支持从完整截图中按 ROI 比例坐标裁剪子图。

#### Scenario: 裁剪 ROI 区域
- **WHEN** 调用 `crop_roi(frame, roi)` 其中 roi 为 `{"x_ratio": 0.42, "y_ratio": 0.03, "w_ratio": 0.12, "h_ratio": 0.04}`
- **THEN** 返回 frame 中对应比例区域的子图（numpy ndarray）

#### Scenario: ROI 超出图像边界
- **WHEN** ROI 区域超出 frame 边界
- **THEN** 自动 clamp 到 frame 有效范围内

### Requirement: 通用模板匹配
系统 SHALL 提供 `match_template` 方法，在指定 ROI 区域内进行模板匹配。

#### Scenario: 匹配成功
- **WHEN** 调用 `match_template(capture, rect, roi, template_path, threshold=0.8)` 且模板图片与截图匹配度 ≥ threshold
- **THEN** 返回 True

#### Scenario: 匹配失败
- **WHEN** 调用 `match_template(capture, rect, roi, template_path, threshold=0.8)` 且模板图片与截图匹配度 < threshold
- **THEN** 返回 False

#### Scenario: 模板图片不存在
- **WHEN** template_path 指向的文件不存在
- **THEN** 打印 warning 日志并返回 False，不崩溃

#### Scenario: OpenCV 不可用
- **WHEN** opencv-python-headless 未安装
- **THEN** 打印 warning 日志并返回 False，不崩溃

### Requirement: 地图界面状态检测
系统 SHALL 提供 `is_map_ui_open` 方法，判断是否在地图界面。

#### Scenario: 地图界面已打开
- **WHEN** 调用 `is_map_ui_open(capture, rect, rois)` 且 map_ui_indicator ROI 区域匹配地图界面特征
- **THEN** 返回 True

#### Scenario: 地图界面未打开
- **WHEN** 调用 `is_map_ui_open(capture, rect, rois)` 且 map_ui_indicator ROI 区域不匹配
- **THEN** 返回 False

#### Scenario: rois 中无 map_ui_indicator
- **WHEN** rois 字典中不包含 "map_ui_indicator" 键
- **THEN** 返回 False 并打印 warning

### Requirement: 格子状态检测
系统 SHALL 提供 `is_slot_empty` 和 `is_slot_occupied` 方法，判断格子占用状态。

#### Scenario: 格子为空
- **WHEN** 调用 `is_slot_empty(capture, rect, slot_verify)` 且格子区域匹配"空"特征
- **THEN** 返回 True

#### Scenario: 格子已占用
- **WHEN** 调用 `is_slot_occupied(capture, rect, slot_verify)` 且格子区域匹配"已占用"特征
- **THEN** 返回 True

#### Scenario: slot_verify 缺少 check_area
- **WHEN** slot_verify 中不包含 "check_area" 键
- **THEN** 返回 False 并打印 warning

### Requirement: 错误提示检测
系统 SHALL 提供 `detect_error_tip` 方法，检测是否出现放置错误提示。

#### Scenario: 检测到错误提示
- **WHEN** 调用 `detect_error_tip(capture, rect, rois)` 且 place_error_tip ROI 区域匹配错误提示特征
- **THEN** 返回 True

#### Scenario: 无错误提示
- **WHEN** 调用 `detect_error_tip(capture, rect, rois)` 且 place_error_tip ROI 区域不匹配
- **THEN** 返回 False

#### Scenario: rois 中无 place_error_tip
- **WHEN** rois 字典中不包含 "place_error_tip" 键
- **THEN** 返回 False

### Requirement: 多帧投票
系统 SHALL 支持多帧投票机制，通过采集多帧后投票决定检测结果，提高检测稳定性。

#### Scenario: 多帧投票多数通过
- **WHEN** 调用 `match_template` 且 config.multi_frame_count > 1，多次采集中超过半数匹配成功
- **THEN** 返回 True

#### Scenario: 多帧投票多数失败
- **WHEN** 调用 `match_template` 且 config.multi_frame_count > 1，多次采集中不超过半数匹配成功
- **THEN** 返回 False

#### Scenario: 单帧模式
- **WHEN** config.multi_frame_count 为 1
- **THEN** 仅采集一帧，直接返回匹配结果

### Requirement: 与 vision/__init__.py 导出集成
系统 SHALL 在 `vision/__init__.py` 中导出 VisionDetector、DetectorConfig。

#### Scenario: 导出可用
- **WHEN** 从 `td_executor.vision` 导入上述类型
- **THEN** 所有类型均可正常导入
