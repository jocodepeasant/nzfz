# OCR 识别引擎 Spec

## Why

automation-executor 目前 `vision/ocr.py` 仅有 `raise NotImplementedError` 的桩函数，无法从游戏截图中识别波次数字、资源数字、核心血量等关键信息。OCR 识别是条件引擎（T06）判断 `resource_gte`、`wave_gte` 等条件的数据来源，也是主循环识别当前波次的基础能力。

## What Changes

- 新增 `read_digits_roi()` 函数：从指定 ROI 区域识别数字文本，返回纯数字字符串
- 新增 `read_wave()` 函数：识别当前波次，支持多帧投票取众数
- 新增 `read_resource()` 函数：识别当前资源数量，支持多帧投票取众数
- 新增 `read_core_hp()` 函数：识别核心血量
- 新增 `_crop_roi()` 内部函数：根据 ROI 比例坐标从截图中裁剪子图
- 新增 `_preprocess_for_digits()` 内部函数：对 ROI 子图做灰度化、二值化等预处理
- 新增 `_ocr_digits()` 内部函数：调用 PaddleOCR 识别数字并清洗结果
- 新增 `_majority_vote()` 内部函数：多帧投票取众数
- PaddleOCR 不可用时优雅降级，打印 warning 并返回 `None`/空字符串

## Impact

- Affected specs: P3（OCR 识别波次、资源）
- Affected code:
  - `automation-executor/src/td_executor/vision/ocr.py`（主要变更）
  - `automation-executor/tests/test_ocr.py`（新增测试）
  - `automation-executor/src/td_executor/vision/__init__.py`（可能更新导出）

## ADDED Requirements

### Requirement: ROI 裁剪

系统 SHALL 提供 `_crop_roi()` 函数，根据 ROI 比例坐标从完整截图中裁剪子图。

#### Scenario: 正常裁剪
- **WHEN** 调用 `_crop_roi(frame, roi)`，其中 roi 为 `{"x_ratio": 0.42, "y_ratio": 0.03, "w_ratio": 0.12, "h_ratio": 0.04}`
- **THEN** 返回根据 `x = int(frame.shape[1] * x_ratio)` 等公式计算的像素区域子图

#### Scenario: ROI 越界保护
- **WHEN** ROI 计算出的像素区域超出 frame 边界
- **THEN** 自动 clamp 到 frame 有效范围内，不抛异常

### Requirement: 数字预处理

系统 SHALL 提供 `_preprocess_for_digits()` 函数，对 ROI 子图做预处理以提升数字识别准确率。

#### Scenario: 灰度化与二值化
- **WHEN** 调用 `_preprocess_for_digits(img)`，img 为 BGR ndarray
- **THEN** 返回经过灰度化 + OTSU 二值化处理后的图像

#### Scenario: OpenCV 不可用
- **WHEN** OpenCV 不可用时调用 `_preprocess_for_digits()`
- **THEN** 返回原始图像不做处理，打印 warning

### Requirement: OCR 数字识别

系统 SHALL 提供 `_ocr_digits()` 函数，调用 PaddleOCR 识别数字并清洗结果。

#### Scenario: 正常识别
- **WHEN** 调用 `_ocr_digits(img)`，img 为预处理后的图像
- **THEN** 调用 PaddleOCR 识别，用正则过滤非数字字符，返回纯数字字符串

#### Scenario: PaddleOCR 不可用
- **WHEN** PaddleOCR 未安装或初始化失败
- **THEN** 打印 warning 并返回空字符串 `""`，不崩溃

#### Scenario: 识别结果无数字
- **WHEN** PaddleOCR 返回的结果中无数字字符
- **THEN** 返回空字符串 `""`

### Requirement: 多帧投票

系统 SHALL 提供 `_majority_vote()` 函数，对多帧识别结果取众数。

#### Scenario: 正常投票
- **WHEN** 调用 `_majority_vote(results)`，results 为 `["5", "5", "6", "5", "4"]`
- **THEN** 返回出现次数最多的值 `"5"`

#### Scenario: 票数相同
- **WHEN** 多个值出现次数相同
- **THEN** 返回列表中第一个出现次数最多的值

#### Scenario: 结果为空
- **WHEN** results 为空列表
- **THEN** 返回 `None`

### Requirement: read_digits_roi

系统 SHALL 提供 `read_digits_roi()` 函数，从指定 ROI 区域识别数字文本。

#### Scenario: 正常识别
- **WHEN** 调用 `read_digits_roi(capture, rect, roi, keyword="wave")`
- **THEN** 截取窗口画面 → 裁剪 ROI → 预处理 → OCR → 返回纯数字字符串

#### Scenario: 识别失败
- **WHEN** OCR 无法识别出数字
- **THEN** 返回空字符串 `""`

### Requirement: read_wave

系统 SHALL 提供 `read_wave()` 函数，识别当前波次。

#### Scenario: 单帧识别
- **WHEN** 调用 `read_wave(capture, rect, rois)` 且 `multi_frame` 为 None
- **THEN** 单帧识别，返回 int 或 None

#### Scenario: 多帧投票
- **WHEN** 调用 `read_wave(capture, rect, rois, multi_frame={"wave_frames": 5})`
- **THEN** 采集 5 帧识别结果，投票取众数，返回 int 或 None

#### Scenario: 识别结果无法转为 int
- **WHEN** 识别结果为空字符串或非数字
- **THEN** 返回 `None`

### Requirement: read_resource

系统 SHALL 提供 `read_resource()` 函数，识别当前资源数量。

#### Scenario: 正常识别
- **WHEN** 调用 `read_resource(capture, rect, rois)`
- **THEN** 返回资源数量的 int 或 None

#### Scenario: 多帧投票
- **WHEN** 调用 `read_resource(capture, rect, rois, multi_frame={"resource_frames": 3})`
- **THEN** 采集 3 帧识别结果，投票取众数

### Requirement: read_core_hp

系统 SHALL 提供 `read_core_hp()` 函数，识别核心血量。

#### Scenario: 正常识别
- **WHEN** 调用 `read_core_hp(capture, rect, rois)`
- **THEN** 返回核心血量的 int 或 None

#### Scenario: 多帧投票
- **WHEN** 调用 `read_core_hp(capture, rect, rois, multi_frame={"core_hp_frames": 3})`
- **THEN** 采集 3 帧识别结果，投票取众数（使用 `slot_state_frames` 作为默认帧数）
