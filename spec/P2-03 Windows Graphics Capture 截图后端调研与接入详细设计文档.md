# P2-03 Windows Graphics Capture 截图后端调研与接入详细设计文档

文档版本：`v1.0`

适用模块：

```text
nzfz_executor/core/screenshot_manager.py
nzfz_executor/core/models.py
tools/wgc_probe.py
experiments/wgc_capture/
```

关联 UI 模块：

```text
ui/tabs/game_connect.py
```

关联前置需求：

```text
P2-01 已连接窗口截图基础能力
P2-02 UI 截图预览与手动刷新
```

适用需求：

```text
P2-03 Windows Graphics Capture 截图后端调研与接入
```

---

# 1. 文档目标

P2-01 已经完成截图基础架构：

```text
ScreenshotManager
ScreenshotBackend
ScreenCaptureBackend
CaptureOptions
ScreenshotResult
CaptureBackendType
```

P2-02 已经完成 UI 截图预览与手动刷新：

```text
刷新截图按钮
截图预览 QLabel
截图状态
截图元信息
后端显示
遮挡支持显示
```

当前基线后端为：

```text
ScreenCaptureBackend
```

其限制是：

```text
只能截取屏幕最终显示内容。
如果目标游戏窗口被其他窗口遮挡，截图可能截到遮挡窗口，而不是游戏窗口自身内容。
```

P2-03 的目标是：

```text
在现有 ScreenshotManager 后端抽象基础上，引入 Windows Graphics Capture 作为高级截图后端，用于增强被遮挡窗口、不在前台窗口的截图能力。
```

但由于 Windows Graphics Capture 涉及系统版本、图形 API、WinRT、Direct3D、权限、游戏渲染方式和反作弊等不确定因素，本需求采用：

```text
技术验证 + 正式接入
```

的两阶段策略。

---

# 2. 设计结论

根据讨论，P2-03 最终采用以下方案：

| 项目 | 结论 |
|---|---|
| 需求名称 | `P2-03 Windows Graphics Capture 截图后端调研与接入` |
| 是否采用两阶段 | 是 |
| 阶段 A | `P2-03A WGC 技术验证` |
| 阶段 B | `P2-03B WindowsGraphicsCaptureBackend 正式接入` |
| 主路线 | Windows Graphics Capture |
| PrintWindow | 仅作为可选调研，不作为主路线 |
| 是否破坏 ScreenCaptureBackend | 否 |
| ScreenCaptureBackend | 永远作为稳定回退 |
| WGC 验证失败是否允许 | 允许 |
| WGC 可用时 AUTO 策略 | 优先 WGC，失败回退 SCREEN |
| 是否支持最小化截图 | 不支持 |
| 是否承诺所有游戏支持 | 不承诺 |
| 是否先做独立验证脚本 | 是 |
| 验证脚本位置 | `tools/wgc_probe.py` 或 `experiments/wgc_capture/` |
| 是否做 UI 大改 | 否 |
| UI 展示 | 复用 P2-02 的后端、遮挡支持、message 元信息 |
| 截图结果类型 | 仍返回 `PIL.Image.Image` |
| WGC 后端能力声明 | `supports_occluded=True` |
| WGC 不可用 | 返回明确失败信息并可回退 SCREEN |

---

# 3. 模块边界

## 3.1 P2-03 负责内容

P2-03 负责：

```text
1. 调研 Windows Graphics Capture 的 Python 可行性
2. 新增独立 WGC 验证脚本
3. 验证是否可通过 hwnd 创建 GraphicsCaptureItem
4. 验证是否可获取一帧窗口图像
5. 验证是否可转换为 PIL Image
6. 验证被遮挡窗口截图效果
7. 验证目标游戏窗口兼容性
8. 将 WGC 能力封装为 WindowsGraphicsCaptureBackend
9. 实现 ScreenshotBackend 接口
10. 设置 supports_occluded=True
11. 接入 ScreenshotManager 后端选择逻辑
12. 将 AUTO 策略升级为优先 WGC，失败回退 SCREEN
13. 在失败时提供明确 message
14. 保证 ScreenCaptureBackend 不受影响
```

---

## 3.2 P2-03 不负责内容

P2-03 不负责：

```text
1. 承诺所有游戏窗口都能被遮挡截图
2. 支持最小化窗口截图
3. 支持隐藏窗口截图
4. 支持独占全屏游戏截图
5. 绕过反作弊或保护机制
6. 复杂 UI 改造
7. 截图保存和历史记录
8. 图像识别
9. OCR
10. 自动点击
11. 执行器主流程
12. 连续录制
13. 高性能视频流捕获
```

---

# 4. 背景与问题

## 4.1 ScreenCaptureBackend 的限制

P2-01 的 `ScreenCaptureBackend` 本质上是：

```text
屏幕区域截图。
```

它使用客户区屏幕坐标，例如：

```python
ImageGrab.grab(bbox=(left, top, right, bottom))
```

该方式截取的是：

```text
屏幕最终合成结果。
```

因此，如果游戏窗口被遮挡：

```text
游戏窗口在后面
浏览器窗口在前面
```

则截图结果可能是：

```text
浏览器窗口内容
```

而不是游戏画面。

---

## 4.2 被遮挡截图的需求

目标能力：

```text
即使目标窗口被其他窗口遮挡，也能获取目标窗口自身画面。
```

这需要使用：

```text
窗口内容捕获
```

而不是：

```text
屏幕区域捕获。
```

---

## 4.3 Windows Graphics Capture 的价值

Windows Graphics Capture，简称 WGC，是 Windows 10 以后提供的现代捕获 API。

它通常用于：

```text
窗口录制
屏幕录制
OBS 类采集
现代截图工具
硬件加速窗口捕获
```

相比 `PrintWindow`，WGC 对现代图形窗口、DirectX 窗口和被遮挡窗口更有希望。

---

# 5. 技术限制声明

P2-03 必须明确以下限制。

## 5.1 不承诺所有游戏可用

WGC 能力受以下因素影响：

```text
游戏渲染 API
DirectX / OpenGL / Vulkan
窗口模式
独占全屏
无边框窗口
系统版本
显卡驱动
DWM 行为
反作弊系统
捕获权限
窗口是否最小化
```

因此 P2-03 不承诺：

```text
所有游戏窗口都能成功捕获。
```

---

## 5.2 不支持最小化窗口截图

即使使用 WGC，最小化窗口也可能：

```text
停止渲染
不产生新帧
返回黑图
返回旧帧
捕获会话失败
```

因此 P2-03 仍然规定：

```text
最小化窗口不支持截图。
```

---

## 5.3 不支持隐藏窗口截图

隐藏窗口通常不具备可捕获的实时画面。

P2-03 仍不支持：

```text
ShowWindow(hwnd, SW_HIDE)
```

等隐藏状态窗口截图。

---

## 5.4 不绕过保护机制

P2-03 不做：

```text
Hook
注入
反作弊绕过
进程内读取渲染缓冲
驱动级捕获
```

---

# 6. P2-03 两阶段策略

## 6.1 P2-03A：WGC 技术验证

目标：

```text
独立验证当前技术栈下是否能通过 hwnd 使用 WGC 获取窗口图像。
```

输出：

```text
tools/wgc_probe.py
```

或：

```text
experiments/wgc_capture/
```

验证内容：

```text
1. 输入 hwnd 或窗口标题
2. 通过 hwnd 创建 GraphicsCaptureItem
3. 创建 Direct3D11 设备
4. 创建 Direct3D11CaptureFramePool
5. 创建 GraphicsCaptureSession
6. 获取一帧图像
7. 将 GPU Texture 转为 CPU 可读数据
8. 转为 PIL Image
9. 保存为 PNG
10. 测试被遮挡窗口截图
11. 测试目标游戏窗口截图
12. 输出兼容性结论
```

---

## 6.2 P2-03B：正式后端接入

目标：

```text
将验证通过的 WGC 能力封装为 WindowsGraphicsCaptureBackend。
```

内容：

```text
1. 新增 WindowsGraphicsCaptureBackend
2. 实现 ScreenshotBackend 接口
3. 设置 backend_type=WINDOWS_GRAPHICS_CAPTURE
4. 设置 supports_occluded=True
5. 接入 ScreenshotManager
6. AUTO 优先选择 WGC
7. WGC 失败时回退 ScreenCaptureBackend
8. 返回 ScreenshotResult
9. UI 通过 P2-02 元信息显示实际后端
```

---

# 7. 推荐目录结构

## 7.1 技术验证目录

二选一。

方案 A：

```text
tools/
└── wgc_probe.py
```

方案 B：

```text
experiments/
└── wgc_capture/
    ├── README.md
    ├── wgc_probe.py
    └── requirements.txt
```

推荐：

```text
experiments/wgc_capture/
```

原因：

```text
WGC 验证可能涉及额外依赖和多次试错，放在 experiments 更清晰。
```

---

## 7.2 正式后端目录

继续使用：

```text
nzfz_executor/core/screenshot_manager.py
```

如果文件过大，可后续拆分：

```text
nzfz_executor/core/capture/
├── __init__.py
├── base.py
├── screen_backend.py
├── wgc_backend.py
└── manager.py
```

P2-03 不强制拆分，除非现有文件已明显膨胀。

---

# 8. WGC 技术验证设计

## 8.1 输入方式

验证脚本支持两种输入：

```text
1. hwnd
2. 窗口标题关键词
```

例如：

```bash
python experiments/wgc_capture/wgc_probe.py --hwnd 123456
```

或：

```bash
python experiments/wgc_capture/wgc_probe.py --title "游戏标题"
```

---

## 8.2 输出方式

输出：

```text
1. 控制台日志
2. PNG 文件
3. 验证结果摘要
```

例如：

```text
output/wgc_capture_20260523_232700.png
```

---

## 8.3 验证场景

必须验证：

| 场景 | 说明 |
|---|---|
| 普通窗口无遮挡 | 基础可用性 |
| 普通窗口被遮挡 | 验证遮挡能力 |
| 游戏窗口无遮挡 | 游戏兼容性 |
| 游戏窗口被遮挡 | 核心目标 |
| 游戏窗口非前台 | 后台捕获能力 |
| 游戏窗口最小化 | 预期失败或不支持 |
| 指定 hwnd 无效 | 错误处理 |
| WGC 不可用 | 错误提示 |

---

## 8.4 验证结论输出

验证完成后应记录：

```text
1. 当前系统版本
2. Python 版本
3. 使用依赖包
4. 普通窗口是否成功
5. 被遮挡普通窗口是否成功
6. 目标游戏是否成功
7. 被遮挡游戏是否成功
8. 最小化行为
9. 截图是否黑屏
10. 是否能稳定返回 PIL Image
11. 是否适合接入正式后端
```

---

# 9. WGC 可用性检测

正式接入时需要提供：

```python
def is_available(self) -> bool:
    ...
```

用于判断当前环境是否支持 WGC。

检查内容包括：

```text
1. 是否 Windows 平台
2. 系统版本是否满足要求
3. 依赖包是否安装
4. 必要 WinRT API 是否可导入
5. Direct3D 初始化是否可用
```

---

## 9.1 后端不可用返回

如果用户指定：

```python
CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
```

但 WGC 不可用，返回：

```python
ScreenshotResult(
    success=False,
    backend=CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE,
    supports_occluded=True,
    message="Windows Graphics Capture 当前不可用，请检查系统版本或依赖环境",
)
```

---

# 10. WindowsGraphicsCaptureBackend 设计

## 10.1 类定义

```python
class WindowsGraphicsCaptureBackend(ScreenshotBackend):
    backend_type = CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
    supports_occluded = True

    def is_available(self) -> bool:
        ...

    def capture(
        self,
        context: ConnectedWindowContext,
        options: CaptureOptions,
    ) -> ScreenshotResult:
        ...
```

---

## 10.2 职责

`WindowsGraphicsCaptureBackend` 负责：

```text
1. 校验 hwnd
2. 校验窗口可见性
3. 校验窗口未最小化
4. 根据 hwnd 创建 WGC 捕获对象
5. 捕获一帧图像
6. 转换为 PIL Image
7. 返回 ScreenshotResult
```

---

## 10.3 不负责

不负责：

```text
1. 保存截图文件
2. 连续录制
3. UI 显示
4. 自动点击
5. 图像识别
6. 反作弊绕过
```

---

# 11. WGC 截图流程

## 11.1 理论流程

```text
输入 hwnd
    ↓
检查 WGC 可用
    ↓
检查窗口有效
    ↓
检查窗口可见
    ↓
检查窗口未最小化
    ↓
通过 hwnd 创建 GraphicsCaptureItem
    ↓
创建 Direct3D11 device
    ↓
创建 Direct3D11CaptureFramePool
    ↓
创建 GraphicsCaptureSession
    ↓
启动 capture session
    ↓
等待一帧
    ↓
获取 frame.Surface / texture
    ↓
复制到 CPU staging texture
    ↓
读取像素数据
    ↓
转换为 PIL Image
    ↓
关闭 session / frame pool
    ↓
返回 ScreenshotResult
```

---

## 11.2 伪代码

```python
def capture(
    self,
    context: ConnectedWindowContext,
    options: CaptureOptions,
) -> ScreenshotResult:
    hwnd = context.hwnd

    if not self.is_available():
        return self._failure(
            context=context,
            options=options,
            message="Windows Graphics Capture 当前不可用，请检查系统版本或依赖环境",
        )

    if not is_window(hwnd):
        return self._failure(
            context=context,
            options=options,
            message="窗口已失效，请重新连接",
        )

    if not is_window_visible(hwnd):
        return self._failure(
            context=context,
            options=options,
            message="窗口不可见，无法截图",
        )

    if is_window_minimized(hwnd):
        return self._failure(
            context=context,
            options=options,
            message="窗口已最小化，无法截图",
        )

    try:
        image = self._capture_one_frame(hwnd)
    except Exception as exc:
        return self._failure(
            context=context,
            options=options,
            message=f"Windows Graphics Capture 截图失败：{exc}",
        )

    window_rect = get_window_rect(hwnd)
    client_rect = get_client_rect_on_screen(hwnd)

    return ScreenshotResult(
        success=True,
        image=image,
        width=image.width,
        height=image.height,
        captured_at=datetime.now(),
        hwnd=hwnd,
        window_title=getattr(context, "title", ""),
        region=options.region,
        backend=self.backend_type,
        window_rect=window_rect,
        client_rect=client_rect,
        supports_occluded=self.supports_occluded,
        message="",
    )
```

---

# 12. 截图区域处理

## 12.1 WGC 捕获内容

WGC 捕获窗口时，返回内容可能更接近：

```text
窗口整体区域
```

而不是严格客户区。

这取决于：

```text
API 创建的 GraphicsCaptureItem
窗口类型
DWM 行为
系统装饰
```

因此 P2-03 必须验证：

```text
WGC 返回图像是否包含标题栏和边框。
```

---

## 12.2 与 CaptureRegion.CLIENT 的关系

P2-01/P2-02 默认使用：

```python
CaptureRegion.CLIENT
```

如果 WGC 返回的是整个窗口，则需要裁剪客户区。

裁剪思路：

```text
1. 获取 window_rect
2. 获取 client_rect
3. 计算 client_rect 相对 window_rect 的偏移
4. 对 WGC 返回图像进行 crop
```

示例：

```python
offset_left = client_rect.left - window_rect.left
offset_top = client_rect.top - window_rect.top

crop_box = (
    offset_left,
    offset_top,
    offset_left + client_rect.width,
    offset_top + client_rect.height,
)

image = image.crop(crop_box)
```

---

## 12.3 注意 DPI 和边框

WGC 图像像素尺寸和 Win32 rect 坐标之间可能存在 DPI 缩放差异。

需要验证：

```text
1. 100% 缩放
2. 125% 缩放
3. 150% 缩放
4. 多显示器不同缩放
```

P2-03 可以先支持主显示器和常规缩放，复杂 DPI 问题后续单独处理。

---

# 13. AUTO 后端选择策略

## 13.1 P2-01 策略

P2-01：

```text
AUTO → SCREEN
```

---

## 13.2 P2-03 策略

P2-03 升级为：

```text
AUTO → WGC if available → SCREEN fallback
```

---

## 13.3 推荐逻辑

```python
def _select_backend(
    self,
    options: CaptureOptions,
) -> ScreenshotBackend:
    if options.backend == CaptureBackendType.AUTO:
        if self._wgc_backend.is_available():
            return self._auto_backend

        return self._screen_backend

    if options.backend == CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE:
        return self._wgc_backend

    if options.backend == CaptureBackendType.SCREEN:
        return self._screen_backend

    return self._unsupported_backend(options.backend)
```

这里有两种实现方式。

---

## 13.4 方案 A：选择 WGC 后不回退

```text
AUTO 选择 WGC，如果 WGC capture 失败，则直接返回失败。
```

优点：

```text
结果明确。
```

缺点：

```text
WGC 偶发失败时用户无法得到截图。
```

---

## 13.5 方案 B：AUTO 捕获失败后回退 SCREEN

```text
AUTO 选择 WGC。
如果 WGC capture 失败，则自动尝试 SCREEN。
```

优点：

```text
更稳。
```

缺点：

```text
如果回退到 SCREEN，则被遮挡时可能截图不准确。
```

---

## 13.6 最终建议

采用方案 B：

```text
AUTO → WGC capture → 若失败则 SCREEN fallback。
```

但 `ScreenshotResult.message` 应说明：

```text
Windows Graphics Capture 不可用或截图失败，已回退到屏幕截图；若窗口被遮挡，截图内容可能不准确。
```

---

# 14. AUTO 回退结果处理

## 14.1 回退场景

当：

```text
options.backend == AUTO
WGC 可用但 capture 失败
SCREEN capture 成功
```

结果应为：

```python
ScreenshotResult(
    success=True,
    backend=CaptureBackendType.SCREEN,
    supports_occluded=False,
    message="Windows Graphics Capture 截图失败，已回退到屏幕截图；若窗口被遮挡，截图内容可能不准确",
)
```

---

## 14.2 指定 WGC 不回退

如果用户明确指定：

```python
CaptureBackendType.WINDOWS_GRAPHICS_CAPTURE
```

则：

```text
不自动回退。
```

原因：

```text
调用方显式要求 WGC，失败应暴露失败结果。
```

---

# 15. ScreenshotManager 修改设计

## 15.1 新增成员

```python
self._screen_backend = ScreenCaptureBackend()
self._wgc_backend = WindowsGraphicsCaptureBackend()
```

---

## 15.2 capture 修改

推荐：

```python
def capture(
    self,
    context: ConnectedWindowContext | None,
    options: CaptureOptions | None = None,
) -> ScreenshotResult:
    options = options or CaptureOptions()

    if context is None:
        return ScreenshotResult(
            success=False,
            region=options.region,
            backend=self._resolve_backend_type(options),
            message="当前未连接游戏窗口",
        )

    if options.backend == CaptureBackendType.AUTO:
        return self._capture_auto(context, options)

    backend = self._select_backend(options)
    return backend.capture(context, options)
```

---

## 15.3 `_capture_auto`

```python
def _capture_auto(
    self,
    context: ConnectedWindowContext,
    options: CaptureOptions,
) -> ScreenshotResult:
    if self._wgc_backend.is_available():
        wgc_result = self._wgc_backend.capture(context, options)
        if wgc_result.success:
            return wgc_result

        screen_result = self._screen_backend.capture(context, options)
        if screen_result.success:
            screen_result.message = (
                "Windows Graphics Capture 截图失败，已回退到屏幕截图；"
                "若窗口被遮挡，截图内容可能不准确"
            )
            return screen_result

        return wgc_result

    screen_result = self._screen_backend.capture(context, options)
    if screen_result.success:
        screen_result.message = (
            "Windows Graphics Capture 当前不可用，已使用屏幕截图；"
            "若窗口被遮挡，截图内容可能不准确"
        )
    return screen_result
```

---

# 16. UI 接入方式

P2-03 不做 UI 大改。

P2-02 已经显示：

```text
尺寸
后端
时间
遮挡支持
message
```

因此 WGC 成功时显示：

```text
尺寸：1280 x 720 | 后端：windows_graphics_capture | 时间：23:27:00 | 遮挡支持：是
```

回退 SCREEN 时显示：

```text
尺寸：1280 x 720 | 后端：screen | 时间：23:27:00 | 遮挡支持：否 | 提示：Windows Graphics Capture 当前不可用，已使用屏幕截图；若窗口被遮挡，截图内容可能不准确
```

---

# 17. Feedback 文案是否需要扩展

P2-03 不强制新增 UI 文案。

可复用：

```text
SCREENSHOT_SUCCESS
SCREENSHOT_FAILED
SCREENSHOT_BACKEND_LIMITED
```

如果需要更明确，可新增：

```python
SCREENSHOT_WGC_UNAVAILABLE
SCREENSHOT_WGC_FALLBACK_SCREEN
```

但 P2-03 不强制，优先通过 `ScreenshotResult.message` 展示。

---

# 18. PrintWindow 调研定位

P2-03 中 PrintWindow 只作为可选调研项。

## 18.1 可做内容

```text
1. 简单验证普通窗口被遮挡截图
2. 验证目标游戏是否黑屏
3. 记录结果
```

---

## 18.2 不做内容

```text
1. 不作为主路线
2. 不作为 AUTO 优先后端
3. 不承诺游戏可用
```

---

## 18.3 后续可能需求

如果 PrintWindow 对某些窗口有价值，可后续新增：

```text
P2-03C PrintWindowCaptureBackend 可选后端
```

---

# 19. 日志规范

## 19.1 WGC 可用性日志

```python
logger.debug("Windows Graphics Capture available: %s", available)
```

---

## 19.2 WGC 捕获失败日志

```python
logger.warning(
    "Windows Graphics Capture failed for hwnd=%s: %s",
    hwnd,
    exc,
)
```

---

## 19.3 AUTO 回退日志

```python
logger.warning(
    "Fallback to ScreenCaptureBackend because WGC failed, hwnd=%s",
    hwnd,
)
```

---

## 19.4 不在用户侧直接暴露

不直接展示：

```text
WinRT 内部异常堆栈
Direct3D HRESULT
COM 指针
GPU texture 细节
```

这些写日志。

---

# 20. 测试用例清单

## 20.1 技术验证测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-WGC-PROBE-001 | 通过 hwnd 捕获普通窗口 | 成功生成 PNG |
| TC-WGC-PROBE-002 | 普通窗口被遮挡 | PNG 是目标窗口内容 |
| TC-WGC-PROBE-003 | 通过标题捕获窗口 | 能解析 hwnd 并截图 |
| TC-WGC-PROBE-004 | hwnd 无效 | 输出明确错误 |
| TC-WGC-PROBE-005 | 游戏窗口无遮挡 | 尝试成功 |
| TC-WGC-PROBE-006 | 游戏窗口被遮挡 | 记录成功/失败结论 |
| TC-WGC-PROBE-007 | 游戏窗口最小化 | 预期失败或无新帧 |
| TC-WGC-PROBE-008 | 截图黑屏 | 记录为兼容性问题 |
| TC-WGC-PROBE-009 | 保存 PNG | 文件可打开 |

---

## 20.2 WGC 后端测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-WGC-BE-001 | WGC 可用性检测 | 返回 True/False |
| TC-WGC-BE-002 | WGC 不可用 | 返回 success=False |
| TC-WGC-BE-003 | hwnd 无效 | 返回 success=False |
| TC-WGC-BE-004 | 窗口不可见 | 返回 success=False |
| TC-WGC-BE-005 | 窗口最小化 | 返回 success=False |
| TC-WGC-BE-006 | WGC 截图成功 | 返回 PIL Image |
| TC-WGC-BE-007 | WGC 截图成功 | backend=WGC |
| TC-WGC-BE-008 | WGC 截图成功 | supports_occluded=True |
| TC-WGC-BE-009 | CLIENT 区域截图 | 图像尺寸符合客户区预期 |
| TC-WGC-BE-010 | WINDOW 区域截图 | 图像尺寸符合窗口区预期 |

---

## 20.3 AUTO 回退测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-WGC-AUTO-001 | WGC 可用且成功 | 使用 WGC |
| TC-WGC-AUTO-002 | WGC 不可用 | 使用 SCREEN |
| TC-WGC-AUTO-003 | WGC 可用但截图失败 | 回退 SCREEN |
| TC-WGC-AUTO-004 | WGC 失败且 SCREEN 成功 | success=True |
| TC-WGC-AUTO-005 | 回退 SCREEN | message 包含回退说明 |
| TC-WGC-AUTO-006 | 明确指定 WGC 失败 | 不回退 SCREEN |
| TC-WGC-AUTO-007 | 明确指定 SCREEN | 不尝试 WGC |

---

## 20.4 UI 验证测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-WGC-UI-001 | WGC 成功截图 | UI 显示后端 WGC |
| TC-WGC-UI-002 | WGC 成功截图 | UI 显示遮挡支持：是 |
| TC-WGC-UI-003 | 回退 SCREEN | UI 显示后端 SCREEN |
| TC-WGC-UI-004 | 回退 SCREEN | UI 显示遮挡支持：否 |
| TC-WGC-UI-005 | 回退 SCREEN | UI 显示回退提示 |
| TC-WGC-UI-006 | WGC 被遮挡截图成功 | UI 图像为目标窗口内容 |

---

# 21. 验收标准

## 21.1 必须验收

P2-03 完成后必须满足：

```text
1. 完成 WGC 技术可行性调研
2. 存在独立验证脚本或实验目录
3. 明确记录当前技术栈是否可通过 hwnd 获取窗口截图
4. 明确记录目标游戏窗口 WGC 兼容性
5. 不破坏 ScreenCaptureBackend
6. ScreenshotManager 支持 WGC 后端类型
7. WGC 不可用时返回明确失败信息
8. AUTO 策略具备 WGC 优先和 SCREEN 回退能力
9. UI 可显示实际使用后端和遮挡支持状态
```

---

## 21.2 技术验证成功时验收

如果 WGC 技术验证成功，则应满足：

```text
1. WindowsGraphicsCaptureBackend 可通过 hwnd 捕获窗口图像
2. 返回 PIL Image
3. 返回 ScreenshotResult
4. backend=WINDOWS_GRAPHICS_CAPTURE
5. supports_occluded=True
6. 被遮挡普通窗口可以捕获目标内容
7. 被遮挡目标游戏窗口测试结果有记录
```

---

## 21.3 不作为验收要求

以下不作为 P2-03 验收要求：

```text
1. 所有游戏窗口都支持
2. 最小化窗口支持
3. 独占全屏游戏支持
4. 反作弊保护窗口支持
5. 所有 DPI 场景完全正确
6. 高性能连续录制
7. 无任何系统捕获提示或边框
```

---

# 22. 风险与应对

## 22.1 Python WGC 调用复杂

风险：

```text
WinRT / Direct3D 在 Python 中调用复杂。
```

应对：

```text
先做 experiments/wgc_capture 技术验证，不直接污染主流程。
```

---

## 22.2 游戏窗口黑屏

风险：

```text
目标游戏窗口可能返回黑屏。
```

应对：

```text
记录兼容性结论，保留 ScreenCaptureBackend 回退。
```

---

## 22.3 DPI 裁剪不准确

风险：

```text
WGC 图像像素与 Win32 rect 坐标存在 DPI 缩放差异。
```

应对：

```text
P2-03 先记录并处理常规 DPI，复杂 DPI 后续单独需求。
```

---

## 22.4 WGC 不可用

风险：

```text
系统版本或依赖不满足。
```

应对：

```text
is_available() 返回 False，AUTO 回退 SCREEN。
```

---

## 22.5 回退后被遮挡截图不准确

风险：

```text
WGC 失败后回退 SCREEN，如果窗口被遮挡，截图可能不准确。
```

应对：

```text
ScreenshotResult.message 明确提示。
```

---

# 23. 实现顺序建议

建议按以下顺序实现：

```text
1. 新建 experiments/wgc_capture/README.md
2. 新建 experiments/wgc_capture/wgc_probe.py
3. 调研 Python 可用依赖
4. 实现 hwnd / title 输入
5. 实现普通窗口 WGC 捕获验证
6. 实现 PNG 输出
7. 测试普通窗口无遮挡
8. 测试普通窗口被遮挡
9. 测试目标游戏无遮挡
10. 测试目标游戏被遮挡
11. 记录验证结论
12. 如果验证成功，新增 WindowsGraphicsCaptureBackend
13. 实现 is_available()
14. 实现 capture()
15. 接入 ScreenshotManager
16. 实现 AUTO 优先 WGC
17. 实现 WGC 失败回退 SCREEN
18. 验证 P2-02 UI 显示实际后端
19. 补充日志
20. 补充测试用例
```

---

# 24. 最终结论

P2-03 的核心目标是：

```text
在现有截图后端抽象基础上，引入 Windows Graphics Capture 作为高级截图后端，增强被遮挡窗口截图能力。
```

本需求采用：

```text
P2-03A 技术验证
P2-03B 正式接入
```

两阶段策略。

P2-03 的原则是：

```text
WGC 是主路线；
PrintWindow 只作为可选调研；
ScreenCaptureBackend 始终作为稳定回退；
不承诺所有游戏可用；
不支持最小化和隐藏窗口截图；
不进行反作弊绕过或 Hook。
```

完成后，如果 WGC 验证成功，截图能力将从：

```text
只能截取屏幕最终画面
```

增强为：

```text
在部分场景下可捕获被遮挡窗口自身内容。
```

同时，即使 WGC 不可用，也不会破坏现有截图流程，而是回退到：

```text
ScreenCaptureBackend
```

并在 UI 中明确提示后端和能力限制。
