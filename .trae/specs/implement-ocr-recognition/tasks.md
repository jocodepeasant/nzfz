# Tasks

- [ ] Task 1: 实现 ROI 裁剪与数字预处理辅助函数
  - [ ] 1.1: 实现 `_crop_roi(frame, roi)` 函数，根据 ROI 比例坐标裁剪子图，含越界保护
  - [ ] 1.2: 实现 `_preprocess_for_digits(img)` 函数，灰度化 + OTSU 二值化，OpenCV 不可用时降级
- [ ] Task 2: 实现 PaddleOCR 封装与数字识别
  - [ ] 2.1: 实现 `_get_ocr_engine()` 懒加载单例，PaddleOCR 不可用时返回 None
  - [ ] 2.2: 实现 `_ocr_digits(img)` 函数，调用 PaddleOCR 识别并用正则清洗返回纯数字字符串
- [ ] Task 3: 实现 `read_digits_roi` 函数
  - [ ] 3.1: 实现 `read_digits_roi(capture, rect, roi, keyword)` 完整流程：截图 → 裁剪 ROI → 预处理 → OCR
- [ ] Task 4: 实现多帧投票与高层识别函数
  - [ ] 4.1: 实现 `_majority_vote(results)` 函数，取众数
  - [ ] 4.2: 实现 `read_wave(capture, rect, rois, multi_frame)` 函数，支持多帧投票
  - [ ] 4.3: 实现 `read_resource(capture, rect, rois, multi_frame)` 函数，支持多帧投票
  - [ ] 4.4: 实现 `read_core_hp(capture, rect, rois, multi_frame)` 函数，支持多帧投票
- [ ] Task 5: 编写单元测试
  - [ ] 5.1: 测试 `_crop_roi` 正常裁剪和越界保护
  - [ ] 5.2: 测试 `_preprocess_for_digits` 预处理逻辑
  - [ ] 5.3: 测试 `_ocr_digits` 正常识别和 PaddleOCR 不可用降级
  - [ ] 5.4: 测试 `_majority_vote` 投票逻辑（正常、票数相同、空列表）
  - [ ] 5.5: 测试 `read_digits_roi` 完整流程（mock ScreenCapture 和 PaddleOCR）
  - [ ] 5.6: 测试 `read_wave` / `read_resource` / `read_core_hp` 单帧和多帧投票
  - [ ] 5.7: 测试 PaddleOCR 全局不可用时所有函数优雅降级

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1] and [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 1] through [Task 4]
