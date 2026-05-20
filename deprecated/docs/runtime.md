# Runtime 模块 — 运行时能力

运行时模块提供与操作系统和硬件交互的底层能力，包括屏幕截图、坐标转换、输入模拟、窗口覆盖层和游戏窗口管理。

## 模块结构

```
runtime/
├── __init__.py      # 模块导出
├── capture.py       # 屏幕采集
├── coordinates.py   # 比例坐标转换
├── input.py         # 输入模拟（点击/按键）
├── overlay.py       # 窗口覆盖层
└── window.py        # 游戏窗口管理
```

---

## capture.py — 屏幕采集模块

### 概述

屏幕采集模块支持两种后端截取游戏窗口画面：`mss`（跨平台）和 `dxcam`（Windows DirectX 加速）。输出格式为 NumPy 数组（BGR 或 RGB）。

### 核心类

#### `CaptureBackend`

截图后端枚举：

| 值 | 说明 |
|---|------|
| `MSS` | 基于 mss 库的截图，跨平台兼容 |
| `DXCAM` | 基于 dxcam 库的 DirectX 截图，仅 Windows |

#### `CaptureConfig`

截图配置数据类。

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `backend` | `CaptureBackend` | `MSS` | 截图后端 |
| `region` | `dict \| None` | `None` | 截图区域（`left`, `top`, `width`, `height`） |
| `output_format` | `str` | `"bgr"` | 输出格式（`bgr` / `rgb`） |

#### `ScreenCapture`

屏幕截图器，支持上下文管理器。

```python
class ScreenCapture:
    def __init__(self, config=None, *, backend="mss", region=None, output_format="bgr")
    def start(self) -> None          # 初始化后端
    def close(self) -> None          # 关闭后端
    def capture_frame(self) -> np.ndarray  # 截取一帧
```

**使用示例：**
```python
with ScreenCapture(region={"left": 0, "top": 0, "width": 1920, "height": 1080}) as cap:
    frame = cap.capture_frame()  # shape: (1080, 1920, 3), dtype: uint8
```

**注意事项：**
- `dxcam` 后端仅支持 Windows，且需要安装 `dxcam` 包
- `mss` 后端在未指定 `region` 时截取全屏
- 关闭后不可重新启动，调用 `capture_frame()` 会抛出 `RuntimeError`

---

## coordinates.py — 比例坐标转换

### 概述

将脚本中的比例坐标（0.0~1.0）转换为窗口像素坐标，实现分辨率无关的定位。

### 核心函数

#### `ratio_to_pixel(window_left, window_top, window_width, window_height, x_ratio, y_ratio) -> tuple[int, int]`

**参数：**
- `window_left`, `window_top` — 窗口左上角屏幕坐标
- `window_width`, `window_height` — 窗口尺寸
- `x_ratio`, `y_ratio` — 比例坐标（0.0~1.0）

**计算公式：**
```
x = window_left + window_width * x_ratio
y = window_top + window_height * y_ratio
```

---

## input.py — 输入模拟

### 概述

输入模拟模块提供跨平台的点击和按键操作。在 Windows 上使用 Win32 `PostMessage` 实现后台输入（不抢占焦点），在非 Windows 平台降级到 `pyautogui` / `pynput`。

### 平台差异

| 功能 | Windows | 非 Windows |
|------|---------|-----------|
| 点击 | `PostMessageW` (WM_LBUTTONDOWN/UP) | `pyautogui.click` |
| 按键 | `PostMessageW` (WM_KEYDOWN/UP) | `pynput.keyboard.Controller` |

### 核心函数

#### `send_click(hwnd, x, y, button="left", game_hwnd=0)`

向指定窗口发送点击消息。

**参数：**
- `hwnd` — 目标窗口句柄（接收消息的窗口）
- `x`, `y` — 坐标（相对于 `game_hwnd` 的客户区坐标）
- `button` — 鼠标按钮（`left` / `right`）
- `game_hwnd` — 游戏窗口句柄，用于坐标转换（默认与 `hwnd` 相同）

**坐标转换流程：**
1. 将 `(x, y)` 从 `game_hwnd` 客户区转换为屏幕坐标（`ClientToScreen`）
2. 若 `hwnd != game_hwnd`，再从屏幕坐标转换到 `hwnd` 客户区（`ScreenToClient`）
3. 构造 `LPARAM` 并发送鼠标消息

#### `send_key(hwnd, key, hold_ms=0)`

向指定窗口发送按键消息。

**参数：**
- `hwnd` — 目标窗口句柄
- `key` — 按键字符
- `hold_ms` — 按住时长（毫秒），0 表示短按

**实现细节：**
- 通过 `VkKeyScanW` 获取虚拟键码
- 构造完整的 `LPARAM`（含扫描码、重复次数等）
- `hold_ms > 0` 时在 KEYDOWN 和 KEYUP 之间插入延时

---

## overlay.py — 窗口覆盖层

### 概述

覆盖层模块在游戏窗口上方创建一个透明分层窗口，用于实时显示操作标记（点击位置、按键信息）和运行日志。仅 Windows 平台完整实现，非 Windows 平台为空操作降级。

### 核心类

#### `WindowOverlay`

透明覆盖层窗口，基于 Win32 分层窗口实现。

```python
class WindowOverlay:
    def show(self, hwnd: int, window_info: str = "") -> bool
    def hide(self) -> bool
    def draw_click_marker(self, x: int, y: int, duration_ms: int = 1500) -> None
    def draw_key_info(self, key: str, hold_ms: int = 0, duration_ms: int = 2000) -> None
    def log_operation(self, msg: str) -> None
```

**窗口特性：**
- `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW` — 透明穿透置顶工具窗口
- 使用颜色键（`COLOR_KEY`）实现透明背景
- 红色边框标识覆盖范围
- 自动同步位置（500ms 定时器），跟随游戏窗口移动/调整大小

**绘制功能：**
- **点击标记**：蓝色十字线，默认显示 1500ms
- **按键信息**：白色描边文字（如"按住 O 4000ms"），默认显示 2000ms
- **运行日志**：绿色等宽字体，底部半透明黑底，最多显示 20 行
- **调试信息**：黄色标题栏文字

**定时器管理：**
- 使用 Win32 `SetTimer` / `KillTimer` 管理标记的自动消失
- 同步定时器 ID 为 9999，每 500ms 触发位置同步
- 标记定时器使用递增 ID，到期后自动清除对应标记

---

## window.py — 游戏窗口管理

### 概述

窗口管理模块负责查找、定位和操作游戏窗口。在 Windows 上使用 Win32 API，非 Windows 平台降级到全屏区域。

### 核心类

#### `WindowRect`

窗口矩形信息数据类。

```python
@dataclass
class WindowRect:
    hwnd: int          # 窗口句柄
    left: int          # 左上角 X（屏幕坐标）
    top: int           # 左上角 Y（屏幕坐标）
    width: int         # 客户区宽度
    height: int        # 客户区高度
    title: str = ""    # 窗口标题
```

### 核心函数

#### `find_game_window(title_keyword="逆战") -> WindowRect | None`

根据标题关键字查找游戏窗口。Windows 上使用 `EnumWindows` 枚举所有可见窗口并匹配标题；非 Windows 平台返回全屏区域作为降级方案。

#### `focus_window(hwnd) -> bool`

将指定窗口置于前台。Windows 上使用 `SetForegroundWindow`，最小化窗口先 `ShowWindow(SW_RESTORE)`。

#### `get_window_rect(hwnd) -> WindowRect | None`

获取指定窗口的客户区矩形（屏幕坐标）。使用 `GetClientRect` + `ClientToScreen` 转换。

#### `is_window_valid(hwnd) -> bool`

检查窗口是否有效且可见。Windows 上使用 `IsWindow` + `IsWindowVisible`。

#### `list_windows(title_keyword="") -> list[dict]`

列出所有可见窗口。返回格式：`[{"hwnd": int, "title": str}]`。可通过 `title_keyword` 过滤。

### 平台降级策略

| 函数 | Windows | 非 Windows |
|------|---------|-----------|
| `find_game_window` | Win32 EnumWindows | mss 全屏区域 / 1920x1080 |
| `focus_window` | SetForegroundWindow | 返回 False |
| `get_window_rect` | GetClientRect + ClientToScreen | mss 全屏区域 / 1920x1080 |
| `is_window_valid` | IsWindow + IsWindowVisible | 返回 True |
| `list_windows` | EnumWindows | 返回空列表 |
