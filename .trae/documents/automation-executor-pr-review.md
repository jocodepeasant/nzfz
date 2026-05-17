# automation-executor PR 代码审查报告

> 审查范围：2026-05-15 ~ 2026-05-17 期间所有与 automation-executor 相关的 PR
> 审查人角色：资深工程师
> 仓库：jocodepeasant/nzfz

---

## 一、PR 概览

| PR | 标题 | 状态 | 变更量 | 核心模块 |
|-----|------|------|--------|---------|
| #2 | feat: 实现游戏窗口管理器并集成到 CLI | ✅ 已合并 | +322/-6 | runtime/window.py, state.py, cli.py |
| #3 | feat: 实现屏幕采集模块并支持 mss/dxcam 后端 | ✅ 已合并 | +419/-5 | runtime/capture.py, runtime/__init__.py |
| #4 | docs: 自动化执行器并行开发任务文档 | ✅ 已合并 | 文档 | .trae/specs/ |
| #6 | feat: 实现单局日志与报告功能 | ✅ 已合并 | +378/-4 | engine/report.py |
| #7 | feat(executor): 实现屏幕采集(T02)与重试框架(T03) | ❌ 已关闭未合并 | +921/-401 | 重复 PR #3 + PR #8 的工作 |
| #8 | feat(executor): 实现重试框架(T03) | ✅ 已合并 | +921/-401 | engine/retry.py |
| #9 | feat: 实现 T04-OCR 识别引擎 | ✅ 已合并 | +689/-27 | vision/ocr.py |
| #10 | feat(executor): 实现模板匹配检测器(T05) | ✅ 已合并 | +679/-55 | vision/detector.py |

**总计**：8 个 PR，7 个已合并，1 个关闭未合并，涉及 ~3400 行新增代码。

---

## 二、严重问题 (Critical / High)

### 🔴 C1: `read_core_hp` 使用了错误的 multi_frame 键名

**文件**: [ocr.py:171](file:///workspace/automation-executor/src/td_executor/vision/ocr.py#L171)

```python
# 当前代码（错误）
if multi_frame is not None and "slot_state_frames" in multi_frame:
    n_frames = multi_frame["slot_state_frames"]
```

`read_core_hp` 检查的是 `"slot_state_frames"` 而非 `"core_hp_frames"`。对比同文件中：
- `read_wave` 使用 `"wave_frames"` ✅
- `read_resource` 使用 `"resource_frames"` ✅
- `read_core_hp` 使用 `"slot_state_frames"` ❌ — 这是 detector 模块的术语，不是 OCR 模块的

**影响**: 如果用户在脚本 JSON 中配置了 `"core_hp_frames": 5`，`read_core_hp` 将完全忽略多帧投票，直接使用单帧结果，降低识别可靠性。

**修复建议**: 将 `"slot_state_frames"` 改为 `"core_hp_frames"`。

---

### 🔴 C2: `crop_roi` 函数重复实现且边界处理不一致

**文件**:
- [ocr.py:23-32](file:///workspace/automation-executor/src/td_executor/vision/ocr.py#L23) — `_crop_roi`
- [detector.py:28-37](file:///workspace/automation-executor/src/td_executor/vision/detector.py#L28) — `crop_roi`

两个函数做完全相同的事情（按 ROI 比例坐标裁剪子图），但边界处理逻辑不同：

```python
# ocr.py 版本 — 先算终点再 clamp
x2 = min(x + w, frame.shape[1])
y2 = min(y + h, frame.shape[0])
x = max(x, 0)
y = max(y, 0)
return frame[y:y2, x:x2]

# detector.py 版本 — 先 clamp 起点再调整宽高
x = max(0, min(x, frame.shape[1]))
y = max(0, min(y, frame.shape[0]))
w = min(w, frame.shape[1] - x)
h = min(h, frame.shape[0] - y)
return frame[y : y + h, x : x + w]
```

**影响**: 当 ROI 超出图像边界时，两个版本产生不同结果。detector.py 版本更正确——它确保切片维度始终有效。ocr.py 版本在极端情况下（如 `x < 0` 且 `x2 < 0`）可能返回空数组或形状异常的数组。

**修复建议**: 提取为 `vision/` 包的公共工具函数（如 `vision/utils.py`），统一使用 detector.py 的边界处理逻辑。

---

### 🔴 C3: OCR 全局可变状态 `_ocr_engine` 缺乏线程安全与重置机制

**文件**: [ocr.py:18-20](file:///workspace/automation-executor/src/td_executor/vision/ocr.py#L18)

```python
_OCR_UNAVAILABLE = object()
_ocr_engine: Any | None = None
```

问题：
1. **无线程安全**: 如果多线程同时调用 `_get_ocr_engine()`，可能创建多个 PaddleOCR 实例
2. **不可恢复**: 一旦初始化失败被标记为 `_OCR_UNAVAILABLE`，整个进程生命周期内 OCR 都不可用，即使后续环境修复也无法重新初始化
3. **测试隔离**: 测试需要 `autouse` fixture 手动重置全局变量，脆弱且易遗漏

**修复建议**: 使用 `threading.Lock` 保护初始化，并提供 `reset_ocr_engine()` 函数用于测试和恢复场景。

---

### 🔴 C4: `VisionDetector.match_template` 多帧模式下首帧被重复采集

**文件**: [detector.py:88-103](file:///workspace/automation-executor/src/td_executor/vision/detector.py#L88)

```python
def match_template(self, ...):
    frame = capture.capture_frame()      # ← 第 1 次采集
    cropped = crop_roi(frame, roi)
    template = _load_template(template_path)
    if template is None:
        return False
    if self._config.multi_frame_count <= 1:
        return _match_single(cropped, template, threshold)
    match_count = 0
    for i in range(self._config.multi_frame_count):
        if i > 0:
            time.sleep(...)
        frame = capture.capture_frame()  # ← 第 2~N 次采集（i=0 时又采一次）
        cropped = crop_roi(frame, roi)
        if _match_single(cropped, template, threshold):
            match_count += 1
```

当 `multi_frame_count > 1` 时，第 88 行采集的帧被完全浪费——循环从 i=0 开始又重新采集。这意味着：
- 实际采集了 N+1 帧，但只用了 N 帧
- 第 88 行和循环 i=0 之间可能有时间差，导致场景变化

**修复建议**: 将首次采集移入循环内，或让循环从 i=0 开始时使用已采集的帧。

---

## 三、中等问题 (Medium)

### 🟡 M1: `read_wave` / `read_resource` / `read_core_hp` 大量重复代码

**文件**: [ocr.py:110-185](file:///workspace/automation-executor/src/td_executor/vision/ocr.py#L110)

三个函数结构几乎完全相同，仅 ROI key 和 multi_frame key 不同。约 75 行重复代码。

**修复建议**: 提取通用函数：
```python
def _read_int_field(capture, rect, rois, roi_key, multi_frame_key, keyword) -> int | None:
    ...
```

---

### 🟡 M2: `ScreenCapture.close()` 未释放 dxcam 后端资源

**文件**: [capture.py:61-68](file:///workspace/automation-executor/src/td_executor/runtime/capture.py#L61)

```python
def close(self) -> None:
    if self._closed:
        return
    self._closed = True
    if self._backend_impl is not None:
        if self._config.backend == CaptureBackend.MSS:
            self._backend_impl.close()   # ← 只处理了 MSS
        self._backend_impl = None         # ← dxcam 没有 release()
```

dxcam 的 camera 对象需要调用 `release()` 方法释放资源，否则可能导致 DirectX 资源泄露。

**修复建议**: 添加 dxcam 的清理逻辑：
```python
elif self._config.backend == CaptureBackend.DXCAM:
    self._backend_impl.release()
```

---

### 🟡 M3: `_find_game_window_fallback` 每次调用都创建新的 `mss.mss()` 实例

**文件**: [window.py:121-129](file:///workspace/automation-executor/src/td_executor/runtime/window.py#L121)

```python
def _find_game_window_fallback(title_keyword: str) -> WindowRect | None:
    try:
        import mss
        monitor = mss.mss().monitors[0]  # ← 每次创建新实例
        ...
```

同样的问题存在于 `_get_window_rect_fallback`（第 137-144 行）。每次调用都创建并销毁 mss 实例，浪费资源。

**修复建议**: 缓存 mss 实例或使用模块级懒加载单例。

---

### 🟡 M4: `GameState` 使用类属性而非实例属性

**文件**: [state.py:11-17](file:///workspace/automation-executor/src/td_executor/state.py#L11)

```python
class GameState:
    wave: int | None = None
    window_handle: int | None = None
    window_rect: WindowRect | None = None
    is_focused: bool = False
```

这些是类属性而非实例属性。虽然对于不可变类型（int, bool, None）不会出问题，但这种模式容易让后续开发者误用（如直接修改类属性影响所有实例）。建议使用 `dataclass` 或在 `__init__` 中定义实例属性。

---

### 🟡 M5: `write_report` 缺乏错误处理

**文件**: [report.py:86-88](file:///workspace/automation-executor/src/td_executor/engine/report.py#L86)

```python
def write_report(path: Path, report: RunReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
```

没有处理 I/O 异常（权限不足、磁盘满、路径非法等）。对于自动化系统，报告写入失败应该至少记录日志或抛出明确异常。

---

### 🟡 M6: `_match_single` 每次调用都 `import cv2`

**文件**: [detector.py:56-57](file:///workspace/automation-executor/src/td_executor/vision/detector.py#L56)

```python
def _match_single(frame, template, threshold):
    import cv2  # ← 每次模板匹配都重新导入
    ...
```

虽然 Python 会缓存已导入的模块，但 `import` 语句仍有查找开销。`VisionDetector.__init__` 已经检查了 cv2 可用性，应该在初始化时缓存 cv2 引用。

---

### 🟡 M7: `RetryConfig.max_count` 默认值为 0，与原始规格不一致

**文件**: [retry.py:23](file:///workspace/automation-executor/src/td_executor/engine/retry.py#L23)

当前默认 `max_count=0`（不重试），而原始 parallel-development-tasks.md 中定义为 `max_count: int = 2`。这意味着默认情况下动作失败后不会重试，可能不符合用户预期。

---

### 🟡 M8: PR #7 关闭未合并——并行开发协调问题

PR #7 尝试在一个 PR 中同时实现 T02 和 T03，但此时 PR #3（T02）已经合并。这导致 PR #7 产生了大量冲突（+921/-401），最终被关闭。PR #8 随后单独实现了 T03。

**问题**: 并行开发缺乏分支协调机制。建议在 parallel-development-tasks.md 中明确每个任务的分支策略，避免多人同时修改同一文件。

---

## 四、低优先级问题 (Low)

### 🟢 L1: 大量 `dict` 参数缺少类型约束

`roi: dict`、`rois: dict`、`slot_verify: dict` 等参数没有指定期望的 key/value 类型。建议使用 `TypedDict` 提升类型安全性和文档价值。

### 🟢 L2: `_load_template` 对相对路径的处理可能不正确

`DetectorConfig.templates_dir` 默认为 `"assets/templates"`（相对路径），`Path(template_path)` 会相对于当前工作目录解析，而非项目根目录。

### 🟢 L3: `_ocr_digits` 对 PaddleOCR 输出格式的解析过于脆弱

`item[1][0]` 这种索引访问依赖 PaddleOCR 的内部返回格式，API 变更会导致运行时错误。

### 🟢 L4: `WindowRect.title` 在构造后被修改

[window.py:73](file:///workspace/automation-executor/src/td_executor/runtime/window.py#L73) 中 `rect.title = title` 修改了已构造的 dataclass 实例。应在构造时传入 title。

### 🟢 L5: `_majority_vote` 平局时行为不确定

`collections.Counter.most_common(1)` 在平局时返回插入顺序靠前的元素，可能导致非确定性结果。

### 🟢 L6: `ScreenCapture.__init__` 同时接受 `config` 和 kwargs 但不校验冲突

当同时传入 `config` 和关键字参数时，config 优先，kwargs 被静默忽略，可能造成用户困惑。

### 🟢 L7: 测试中 `_preprocess_for_digits` 使用了侵入式 `builtins.__import__` patch

[test_ocr.py:88-97](file:///workspace/automation-executor/tests/test_ocr.py#L88) 的 `test_cv2_import_error_returns_original` 测试 patch 了 `builtins.__import__`，这种方式过于侵入性，应使用 `patch.dict("sys.modules", {"cv2": None})` 替代。

### 🟢 L8: 模块缺少日志配置

所有模块使用 `logging.getLogger(__name__)` 但没有配置 handler。用户需要自行配置 logging 才能看到降级 warning，否则关键信息可能丢失。

---

## 五、架构与设计评价

### 优点

1. **优雅降级设计一致**: OCR、检测器、窗口管理器都实现了依赖不可用时的优雅降级，打印 warning 并返回安全默认值，不崩溃。这对生产环境非常重要。

2. **Lazy Init 模式**: `ScreenCapture` 和 PaddleOCR 都采用懒加载，避免在 import 时就触发重量级依赖的初始化。

3. **回调注入**: `RetryManager.execute_with_retry` 通过回调函数注入具体动作，不依赖任何业务逻辑，设计干净。

4. **测试覆盖充分**: 每个模块都有对应的单元测试，覆盖了正常路径、异常路径和降级场景。总测试数 33+29+48+201+164 = ~475 个测试用例。

5. **跨平台兼容**: 窗口管理器对 Windows 和非 Windows 平台提供了不同的实现路径。

### 需要改进

1. **代码重复**: `crop_roi`、`read_wave/read_resource/read_core_hp` 存在明显的重复代码，应提取公共实现。

2. **全局可变状态**: OCR 引擎的全局单例模式需要加强线程安全和可重置性。

3. **类型安全**: 大量使用裸 `dict` 类型，缺少 `TypedDict` 约束，IDE 无法提供智能提示。

4. **资源管理**: dxcam 后端的资源释放、mss 实例的重复创建等问题需要关注。

---

## 六、修复优先级建议

| 优先级 | 编号 | 修复建议 | 预估工作量 |
|--------|------|---------|-----------|
| P0 紧急 | C1 | 修正 `read_core_hp` 的 multi_frame 键名 | 5 分钟 |
| P0 紧急 | C4 | 修正 `match_template` 多帧首帧重复采集 | 15 分钟 |
| P1 高 | C2 | 统一 `crop_roi` 实现，提取为公共工具 | 30 分钟 |
| P1 高 | C3 | OCR 引擎全局状态加锁 + 重置函数 | 30 分钟 |
| P2 中 | M1 | 提取 `read_wave/resource/core_hp` 公共逻辑 | 20 分钟 |
| P2 中 | M2 | dxcam 后端资源释放 | 10 分钟 |
| P2 中 | M3 | mss 实例缓存 | 15 分钟 |
| P2 中 | M6 | cv2 引用缓存 | 10 分钟 |
| P3 低 | M4/M5/M7/L1-L8 | 各类小改进 | 按需 |

---

## 七、实施步骤

1. **立即修复 C1 和 C4**（P0 级 bug，影响运行时正确性）
2. **提取公共 `crop_roi`** 到 `vision/utils.py`，统一边界处理逻辑
3. **为 OCR 引擎添加线程锁和重置函数**
4. **重构 OCR 三个 read 函数为通用实现**
5. **修复 dxcam 资源释放和 mss 实例缓存**
6. **其余低优先级问题在后续迭代中逐步解决**
