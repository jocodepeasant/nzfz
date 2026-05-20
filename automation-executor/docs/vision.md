# Vision 模块 — 视觉识别

视觉模块提供基于 OpenCV 模板匹配的界面状态检测和基于 PaddleOCR 的数字识别能力，是自动化执行器的"眼睛"。

## 模块结构

```
vision/
├── __init__.py      # 模块导出
├── detector.py      # 模板匹配检测器
└── ocr.py           # OCR 数字识别
```

---

## detector.py — 模板匹配检测器

### 概述

检测器模块使用 OpenCV 模板匹配（`cv2.matchTemplate` + `TM_CCOEFF_NORMED`）判断游戏界面的各种状态，包括地图 UI 是否打开、格子是否为空/已占用、是否出现错误提示等。

支持多帧投票机制，通过多次截图匹配取多数结果，提高检测鲁棒性。

### 核心类

#### `DetectorConfig`

检测器配置数据类。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `match_threshold` | `float` | `0.8` | 模板匹配阈值（0~1） |
| `multi_frame_count` | `int` | `3` | 多帧投票帧数 |
| `multi_frame_interval_ms` | `int` | `100` | 多帧间隔（毫秒） |
| `templates_dir` | `str` | `"assets/templates"` | 模板图片目录 |

#### `VisionDetector`

视觉检测器主类。

```python
class VisionDetector:
    def __init__(self, config: DetectorConfig | None = None)
    def match_template(self, capture, rect, roi, template_path, threshold=None) -> bool
    def is_map_ui_open(self, capture, rect, rois) -> bool
    def is_slot_empty(self, capture, rect, slot_verify) -> bool
    def is_slot_occupied(self, capture, rect, slot_verify) -> bool
    def detect_error_tip(self, capture, rect, rois) -> bool
```

**`match_template` 执行流程：**
1. 截取当前帧
2. 根据 ROI 裁剪目标区域
3. 加载模板图片
4. 若 `multi_frame_count > 1`：多次截图匹配，超过半数匹配成功则返回 `True`
5. 若 `multi_frame_count <= 1`：单次匹配

### 检测方法

| 方法 | 模板文件 | ROI 来源 | 说明 |
|------|---------|---------|------|
| `is_map_ui_open` | `map_ui_indicator.png` | `rois["map_ui_indicator"]` | 若 ROI 未配置则默认返回 `True` |
| `is_slot_empty` | `slot_empty.png` | `slot_verify["check_area"]` | 格子为空检测 |
| `is_slot_occupied` | `slot_occupied.png` | `slot_verify["check_area"]` | 格子已占用检测 |
| `detect_error_tip` | `place_error_tip.png` | `rois["place_error_tip"]` | 放置错误提示检测 |

### 工具函数

#### `crop_roi(frame: np.ndarray, roi: dict) -> np.ndarray`

根据 ROI 比例坐标裁剪帧图像。

**ROI 格式：**
```json
{
    "x_ratio": 0.1,
    "y_ratio": 0.2,
    "w_ratio": 0.3,
    "h_ratio": 0.1
}
```

---

## ocr.py — OCR 数字识别

### 概述

OCR 模块基于 PaddleOCR 实现游戏界面中的数字识别，主要用于读取波次、资源和核心血量等数值。支持多帧投票机制提高识别准确率。

### 核心函数

#### `read_wave(capture, rect, rois, multi_frame=None) -> int | None`

读取当前波次数值。

**流程：**
1. 从 `rois["wave"]` 获取波次 ROI
2. 截图并裁剪 ROI 区域
3. 灰度化 + OTSU 二值化预处理
4. PaddleOCR 识别，提取数字
5. 若配置了 `multi_frame["wave_frames"]`，多帧投票取众数
6. 转换为整数返回

#### `read_resource(capture, rect, rois, multi_frame=None) -> int | None`

读取当前资源数值。流程与 `read_wave` 类似，使用 `rois["resource"]` ROI。

#### `read_core_hp(capture, rect, rois, multi_frame=None) -> int | None`

读取核心血量。使用 `rois["core_hp"]` ROI，多帧配置键为 `slot_state_frames`。

#### `read_digits_roi(capture, rect, roi, keyword="") -> str`

底层 OCR 识别函数，对指定 ROI 进行数字识别。

**流程：**
1. 截取当前帧
2. 裁剪 ROI 区域
3. 灰度化 + OTSU 二值化
4. PaddleOCR 识别
5. 正则提取所有数字字符拼接返回

### 内部实现

#### OCR 引擎初始化

PaddleOCR 引擎采用懒加载单例模式：
- 首次调用时初始化（`use_angle_cls=False, lang="en"`）
- 初始化失败后标记为不可用，后续不再尝试
- 配置 `show_log=False` 减少日志输出

#### 图像预处理（`_preprocess_for_digits`）

1. BGR → 灰度
2. OTSU 自适应二值化

#### 多帧投票（`_majority_vote`）

使用 `collections.Counter` 统计多次识别结果，返回出现次数最多的值。

### 依赖

| 库 | 用途 | 必需 |
|---|------|------|
| `paddleocr` | OCR 识别引擎 | 是 |
| `cv2` (OpenCV) | 图像预处理 | 是 |
| `numpy` | 数组操作 | 是 |
