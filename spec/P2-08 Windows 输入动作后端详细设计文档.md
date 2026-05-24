# P2-08 Windows 输入动作后端详细设计文档

文档版本：`v1.0`

适用模块：

```text
ui/config/defaults.py
ui/tabs/game_connect.py
ui/workers/executor_workers.py

nzfz_executor/core/actions/__init__.py
nzfz_executor/core/actions/models.py
nzfz_executor/core/actions/mouse_controller.py
nzfz_executor/core/actions/safety.py

nzfz_executor/core/actions/backends/__init__.py
nzfz_executor/core/actions/backends/base.py
nzfz_executor/core/actions/backends/dry_run_backend.py
nzfz_executor/core/actions/backends/send_input_backendP2-09py
```

关联前置需求：

```text
P2-05 执行任务异步化与停止机制
P2-06 执行日志与结果反馈
P2-07 图像识别与执行动作接入（最小闭环）
```

后续关联需求：

```text
P2-09 模板匹配与资源管理
P2-10 自动化任务配置与流程编排
P2-xx 应用配置中心与用户设置
P2-xx 窗口激活与前台管理
P2-xx PostMessage 输入后端
```

适用需求：

```text
P2-08 Windows 输入动作后端
```

---

# 1. 文档目标

P2-07 已经将执行器从占位循环升级为最小自动化闭环：

```text
截图 → 识别 → 坐标映射 → 动作执行 → 日志反馈
```

其中动作执行使用：

```text
MouseController.click()
```

但 P2-07 中 `MouseController` 的真实点击能力尚未实现：

```text
dry-run=True  → 返回成功，但不真实点击
dry-run=False → 返回失败，提示真实点击尚未实现
```

P2-08 的目标是：

```text
为 MouseController 接入 Windows 鼠标输入后端，在 dry-run 关闭时支持真实点击，并提供安全校验、动作日志、失败反馈和可扩展输入后端结构。
```

本阶段仍然默认保持：

```python
DEFAULT_ACTION_DRY_RUN = True
```

也就是说：

```text
实现真实点击能力，但默认不启用真实点击。
```

---

# 2. 设计结论

P2-08 最终采用以下方案：

| 项目 | 结论 |
|---|---|
| 需求名称 | `P2-08 Windows 输入动作后端` |
| 默认行为 | 继续 `dry-run` |
| 是否实现真实点击 | 是 |
| 是否默认启用真实点击 | 否 |
| 真实点击后端 | `SetCursorPos + SendInput down/up` |
| 是否实现 PostMessage | 否 |
| 是否实现 pyautogui | 否 |
| 是否主动激活窗口 | 否 |
| 是否新增后端抽象 | 是 |
| 后端接口 | `MouseInputBackend` |
| dry-run 后端 | `DryRunMouseBackend` |
| Windows 后端 | `SendInputMouseBackend` |
| Controller 设计 | `MouseController` 组合 backend |
| 默认 Controller 工厂 | `MouseController.create_default(dry_run)` |
| 安全校验 | 是 |
| 安全校验器 | `ActionSafetyGuard` |
| 校验结果 | `ActionValidationResult` |
| 点击安全条件 | 坐标必须在连接窗口矩形内 |
| click 参数 | `click(action, context=ctx.connected_context)` |
| 支持按钮 | `LEFT / RIGHT / MIDDLE` |
| 点击按下时长 | 使用 `ClickAction.duration_ms` |
| UI 开关 | 不做 |
| 配置持久化 | 不做 |

---

# 3. 模块边界

## 3.1 P2-08 负责内容

P2-08 负责：

```text
1. 新增 MouseInputBackend 协议
2. 新增 DryRunMouseBackend
3. 新增 SendInputMouseBackend
4. 使用 SetCursorPos + SendInput 实现真实点击
5. 支持 LEFT / RIGHT / MIDDLE 鼠标按钮
6. 支持 duration_ms 控制按下时长
7. 改造 MouseController 为后端组合模式
8. 提供 MouseController.create_default(dry_run)
9. 新增 ActionSafetyGuard
10. 新增 ActionValidationResult
11. 点击前校验坐标是否在连接窗口矩形内
12. 修改 MouseController.click(action, context)
13. 修改 ExecutorWorker 调用方式
14. 保持 DEFAULT_ACTION_DRY_RUN=True
```

---

## 3.2 P2-08 不负责内容

P2-08 不负责：

```text
1. 不默认启用真实点击
2. 不做 UI 上的真实点击开关
3. 不做配置持久化
4. 不做设置页
5. 不实现 PostMessage 后端
6. 不实现 SendMessage 后端
7. 不实现 pyautogui 后端
8. 不实现鼠标轨迹模拟
9. 不实现窗口主动激活
10. 不实现窗口置顶
11. 不处理反作弊限制
12. 不处理 UAC 高权限注入问题
13. 不处理复杂 DPI 坐标校准
14. 不实现动作重试
15. 不实现动作队列
```

---

# 4. 配置项

## 4.1 保持默认 dry-run

文件：

```text
ui/config/defaults.py
```

保持：

```python
DEFAULT_ACTION_DRY_RUN = True
```

这是 P2-08 的重要安全约束。

---

## 4.2 推荐配置内容

```python
from __future__ import annotations

DEFAULT_MAX_EXECUTOR_LOG_LINES = 1000

DEFAULT_SCREENSHOT_TIMEOUT_MS = 5_000
DEFAULT_EXECUTOR_STOP_TIMEOUT_MS = 10_000

DEFAULT_EXECUTOR_LOG_TIME_FORMAT = "%H:%M:%S"
DEFAULT_EXECUTOR_PROGRESS_LOG_ENABLED = True

DEFAULT_ACTION_DRY_RUN = True
DEFAULT_EXECUTOR_MAX_ITERATIONS = 1
DEFAULT_EXECUTOR_LOOP_INTERVAL_MS = 500
```

---

## 4.3 后续配置化方向

后续配置中心可支持：

```text
actions.dry_run
actions.backend
actions.click_duration_ms
actions.safety_check_enabled
actions.require_window_foreground
```

P2-08 不实现这些配置持久化。

---

# 5. 动作模型调整

## 5.1 文件

```text
nzfz_executor/core/actions/models.py
```

---

## 5.2 P2-07 已有模型

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ScreenPoint:
    x: int
    y: int


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass(frozen=True)
class ClickAction:
    point: ScreenPoint
    button: MouseButton = MouseButton.LEFT
    duration_ms: int = 50


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str = ""
```

---

## 5.3 P2-08 新增 ActionValidationResult

```python
@dataclass(frozen=True)
class ActionValidationResult:
    valid: bool
    message: str = ""
```

---

## 5.4 完整推荐代码

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ScreenPoint:
    x: int
    y: int


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass(frozen=True)
class ClickAction:
    point: ScreenPoint
    button: MouseButton = MouseButton.LEFT
    duration_ms: int = 50


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str = ""


@dataclass(frozen=True)
class ActionValidationResult:
    valid: bool
    message: str = ""
```

---

# 6. 安全校验设计

## 6.1 新增文件

```text
nzfz_executor/core/actions/safety.py
```

---

## 6.2 设计目标

真实点击前必须进行最小安全校验：

```text
点击坐标必须落在当前连接窗口矩形内。
```

如果坐标不在窗口范围内，则拒绝动作。

---

## 6.3 校验规则

假设窗口矩形为：

```text
left <= x < right
top <= y < bottom
```

点击点为：

```text
screen=(x,y)
```

则有效条件：

```text
left <= point.x < right
top <= point.y < bottom
```

---

## 6.4 推荐代码

```python
from __future__ import annotations

from nzfz_executor.core.actions.models import (
    ActionValidationResult,
    ClickAction,
)
from nzfz_executor.core.models import ConnectedWindowContext


class ActionSafetyGuard:
    def validate_click(
        self,
        action: ClickAction,
        context: ConnectedWindowContext | None,
    ) -> ActionValidationResult:
        if context is None:
            return ActionValidationResult(
                valid=False,
                message="动作安全校验失败：连接上下文为空",
            )

        rect = context.window_rect
        point = action.point

        if not (
            rect.left <= point.x < rect.right
            and rect.top <= point.y < rect.bottom
        ):
            return ActionValidationResult(
                valid=False,
                message=(
                    "动作安全校验失败：点击坐标超出连接窗口范围，"
                    f"point=({point.x},{point.y}), "
                    f"window=({rect.left},{rect.top},"
                    f"{rect.right},{rect.bottom})"
                ),
            )

        return ActionValidationResult(
            valid=True,
            message="动作安全校验通过",
        )
```

---

## 6.5 模型适配说明

如果当前 `ConnectedWindowContext` 的窗口矩形字段不是：

```python
context.window_rect.left
context.window_rect.top
context.window_rect.right
context.window_rect.bottom
```

实现时按现有模型适配。

---

# 7. 输入后端抽象

## 7.1 新增目录

```text
nzfz_executor/core/actions/backends/
```

新增：

```text
nzfz_executor/core/actions/backends/__init__.py
nzfz_executor/core/actions/backends/base.py
nzfz_executor/core/actions/backends/dry_run_backend.py
nzfz_executor/core/actions/backends/send_input_backend.py
```

---

## 7.2 `backends/base.py`

```python
from __future__ import annotations

from typing import Protocol

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
)
from nzfz_executor.core.models import ConnectedWindowContext


class MouseInputBackend(Protocol):
    def click(
        self,
        action: ClickAction,
        context: ConnectedWindowContext | None = None,
    ) -> ActionResult:
        ...
```

---

# 8. DryRunMouseBackend

## 8.1 文件

```text
nzfz_executor/core/actions/backends/dry_run_backend.py
```

---

## 8.2 推荐实现

```python
from __future__ import annotations

from nzfz_executor.core.actions.backends.base import MouseInputBackend
from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
)
from nzfz_executor.core.models import ConnectedWindowContext


class DryRunMouseBackend:
    def click(
        self,
        action: ClickAction,
        context: ConnectedWindowContext | None = None,
    ) -> ActionResult:
        point = action.point

        return ActionResult(
            success=True,
            message=(
                "dry-run：跳过真实点击 "
                f"screen=({point.x},{point.y}), "
                f"button={action.button.value}"
            ),
        )
```

---

## 8.3 dry-run 是否做安全校验

P2-08 建议：

```text
dry-run 不强制做安全校验。
```

原因：

```text
1. dry-run 不会真实点击
2. 可用于观察坐标映射是否超出窗口
3. 避免早期调试时被安全校验阻断
```

但日志仍会显示坐标。

后续可以配置化：

```text
dry-run 是否也执行安全校验
```

---

# 9. SendInputMouseBackend

## 9.1 文件

```text
nzfz_executor/core/actions/backends/send_input_backend.py
```

---

## 9.2 实现策略

P2-08 使用：

```text
SetCursorPos(x, y)
SendInput(mouse down)
sleep(duration_ms)
SendInput(mouse up)
```

说明：

```text
1. SetCursorPos 将真实鼠标移动到目标坐标
2. SendInput 发送鼠标按下和抬起事件
3. duration_ms 控制按下到抬起之间的间隔
```

---

## 9.3 为什么不用 SendInput 绝对坐标移动

SendInput 绝对坐标需要映射到：

```text
0 ~ 65535
```

且在多显示器、DPI 缩放、虚拟屏幕坐标场景下容易出错。

P2-08 初版采用：

```text
SetCursorPos + SendInput button
```

更简单、可验证。

---

## 9.4 ctypes 常量

```python
INPUT_MOUSE = 0

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
```

---

## 9.5 鼠标按钮映射

```python
_BUTTON_FLAGS = {
    MouseButton.LEFT: (
        MOUSEEVENTF_LEFTDOWN,
        MOUSEEVENTF_LEFTUP,
    ),
    MouseButton.RIGHT: (
        MOUSEEVENTF_RIGHTDOWN,
        MOUSEEVENTF_RIGHTUP,
    ),
    MouseButton.MIDDLE: (
        MOUSEEVENTF_MIDDLEDOWN,
        MOUSEEVENTF_MIDDLEUP,
    ),
}
```

---

## 9.6 推荐代码

```python
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
    MouseButton,
)
from nzfz_executor.core.actions.safety import ActionSafetyGuard
from nzfz_executor.core.models import ConnectedWindowContext


INPUT_MOUSE = 0

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


_BUTTON_FLAGS = {
    MouseButton.LEFT: (
        MOUSEEVENTF_LEFTDOWN,
        MOUSEEVENTF_LEFTUP,
    ),
    MouseButton.RIGHT: (
        MOUSEEVENTF_RIGHTDOWN,
        MOUSEEVENTF_RIGHTUP,
    ),
    MouseButton.MIDDLE: (
        MOUSEEVENTF_MIDDLEDOWN,
        MOUSEEVENTF_MIDDLEUP,
    ),
}


class SendInputMouseBackend:
    def __init__(
        self,
        safety_guard: ActionSafetyGuard | None = None,
    ) -> None:
        self._safety_guard = safety_guard or ActionSafetyGuard()

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindowContext | None = None,
    ) -> ActionResult:
        validation = self._safety_guard.validate_click(
            action=action,
            context=context,
        )
        if not validation.valid:
            return ActionResult(
                success=False,
                message=validation.message,
            )

        point = action.point

        try:
            if not ctypes.windll.user32.SetCursorPos(
                int(point.x),
                int(point.y),
            ):
                return ActionResult(
                    success=False,
                    message=(
                        "真实点击失败：SetCursorPos 调用失败"
                    ),
                )

            down_flag, up_flag = self._get_button_flags(action.button)

            self._send_mouse_flag(down_flag)

            duration = max(0, action.duration_ms) / 1000
            if duration > 0:
                time.sleep(duration)

            self._send_mouse_flag(up_flag)

            return ActionResult(
                success=True,
                message=(
                    "真实点击完成 "
                    f"screen=({point.x},{point.y}), "
                    f"button={action.button.value}"
                ),
            )

        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"真实点击异常：{exc}",
            )

    def _get_button_flags(
        self,
        button: MouseButton,
    ) -> tuple[int, int]:
        if button not in _BUTTON_FLAGS:
            raise ValueError(f"不支持的鼠标按钮：{button}")

        return _BUTTON_FLAGS[button]

    def _send_mouse_flag(self, flag: int) -> None:
        input_struct = INPUT(
            type=INPUT_MOUSE,
            union=INPUT_UNION(
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=flag,
                    time=0,
                    dwExtraInfo=None,
                ),
            ),
        )

        sent = ctypes.windll.user32.SendInput(
            1,
            ctypes.byref(input_struct),
            ctypes.sizeof(INPUT),
        )

        if sent != 1:
            raise RuntimeError(
                f"SendInput 调用失败，sent={sent}"
            )
```

---

## 9.7 注意事项

`ctypes.windll.user32` 仅适用于 Windows。

如果未来需要跨平台，应在后端选择阶段判断平台。

P2-08 默认项目场景为 Windows。

---

# 10. MouseController 改造

## 10.1 文件

```text
nzfz_executor/core/actions/mouse_controller.py
```

---

## 10.2 P2-07 旧版

```python
class MouseController:
    def __init__(self, dry_run: bool = True) -> None:
        self._dry_run = dry_run

    def click(self, action: ClickAction) -> ActionResult:
        ...
```

---

## 10.3 P2-08 新版设计

```python
MouseController
    ↓
MouseInputBackend
    ├── DryRunMouseBackend
    └── SendInputMouseBackend
```

---

## 10.4 推荐代码

```python
from __future__ import annotations

from nzfz_executor.core.actions.backends.base import MouseInputBackend
from nzfz_executor.core.actions.backends.dry_run_backend import (
    DryRunMouseBackend,
)
from nzfz_executor.core.actions.backends.send_input_backend import (
    SendInputMouseBackend,
)
from nzfz_executor.core.actions.models import (
    ActionResult,
    ClickAction,
)
from nzfz_executor.core.models import ConnectedWindowContext


class MouseController:
    def __init__(self, backend: MouseInputBackend) -> None:
        self._backend = backend

    @classmethod
    def create_default(cls, dry_run: bool = True) -> "MouseController":
        if dry_run:
            backend = DryRunMouseBackend()
        else:
            backend = SendInputMouseBackend()

        return cls(backend=backend)

    def click(
        self,
        action: ClickAction,
        context: ConnectedWindowContext | None = None,
    ) -> ActionResult:
        return self._backend.click(
            action=action,
            context=context,
        )
```

---

## 10.5 为什么使用 create_default

这样 UI 层只需要：

```python
MouseController.create_default(
    dry_run=DEFAULT_ACTION_DRY_RUN,
)
```

不需要知道：

```text
DryRunMouseBackend
SendInputMouseBackend
```

后续可以根据配置扩展：

```python
MouseController.create_from_config(config)
```

---

# 11. ExecutorWorker 调整

## 11.1 P2-07 调用

P2-07 中动作调用可能是：

```python
result = ctx.mouse_controller.click(action)
```

---

## 11.2 P2-08 调整为

```python
result = ctx.mouse_controller.click(
    action,
    context=ctx.connected_context,
)
```

---

## 11.3 修改位置

文件：

```text
ui/workers/executor_workers.py
```

在 `_run_one_iteration()` 的 Act 阶段：

```python
action = ClickAction(point=screen_point)
result = ctx.mouse_controller.click(
    action,
    context=ctx.connected_context,
)

if not result.success:
    raise RuntimeError(result.message or "动作执行失败")

self._emit_log(result.message or "动作执行成功")
```

---

# 12. game_connect.py 调整

## 12.1 P2-07 创建 MouseController

P2-07 可能是：

```python
mouse_controller=MouseController(
    dry_run=DEFAULT_ACTION_DRY_RUN,
)
```

---

## 12.2 P2-08 改为

```python
mouse_controller=MouseController.create_default(
    dry_run=DEFAULT_ACTION_DRY_RUN,
)
```

---

## 12.3 推荐代码

```python
runtime_context = ExecutorRuntimeContext(
    connected_context=context,
    screenshot_manager=self._screenshot_manager,
    recognizer=CenterPointRecognizer(),
    coordinate_mapper=CoordinateMapper(),
    mouse_controller=MouseController.create_default(
        dry_run=DEFAULT_ACTION_DRY_RUN,
    ),
    max_iterations=DEFAULT_EXECUTOR_MAX_ITERATIONS,
    loop_interval_ms=DEFAULT_EXECUTOR_LOOP_INTERVAL_MS,
)
```

---

# 13. 日志表现

## 13.1 dry-run 默认日志

默认配置：

```python
DEFAULT_ACTION_DRY_RUN = True
```

执行日志仍然显示：

```text
dry-run：跳过真实点击 screen=(1234,567), button=left
```

---

## 13.2 真实点击日志

如果开发者临时改为：

```python
DEFAULT_ACTION_DRY_RUN = False
```

动作成功时：

```text
真实点击完成 screen=(1234,567), button=left
```

动作失败时：

```text
任务执行失败：动作安全校验失败：点击坐标超出连接窗口范围...
```

或：

```text
任务执行失败：真实点击异常：xxx
```

---

# 14. 安全策略

## 14.1 已实现安全策略

P2-08 至少实现：

```text
点击坐标必须在连接窗口矩形内。
```

---

## 14.2 不实现的安全策略

P2-08 不实现：

```text
1. 检查窗口是否前台
2. 检查窗口是否被遮挡
3. 点击前激活窗口
4. 点击前确认鼠标当前位置
5. 点击前用户二次确认
6. 点击区域黑名单
7. 点击频率限制
8. 点击重试
```

---

## 14.3 用户风险提示

由于 P2-08 不做 UI 设置页，也不默认启用真实点击，因此暂不增加 UI 风险提示。

后续在设置页启用真实点击时，应增加：

```text
启用真实点击可能移动鼠标并操作当前屏幕，请确保目标窗口可见且未被遮挡。
```

---

# 15. 窗口激活策略

P2-08 明确：

```text
不主动激活窗口。
```

原因：

```text
1. SetForegroundWindow 有系统限制
2. 主动抢焦点可能影响用户
3. 某些游戏窗口激活行为复杂
4. P2-08 只负责输入后端，不负责窗口焦点管理
```

后续可新增：

```text
P2-xx 窗口激活与前台管理
```

---

# 16. 平台限制

`SendInputMouseBackend` 使用：

```python
ctypes.windll.user32
```

因此仅适用于：

```text
Windows
```

如果未来需要跨平台，应在：

```python
MouseController.create_default()
```

或配置工厂中检测平台：

```python
if not sys.platform.startswith("win"):
    return DryRunMouseBackend()
```

P2-08 暂不强制实现跨平台兼容。

---

# 17. 与 P2-07 的兼容性

P2-08 改动后，P2-07 的最小闭环仍然成立：

```text
截图
识别中心点
坐标映射
MouseController.click()
```

区别是：

```text
dry_run=True  → DryRunMouseBackend
dry_run=False → SendInputMouseBackend
```

默认行为不变：

```text
dry-run
```

所以不会改变用户默认体验。

---

# 18. 与后续需求的衔接

## 18.1 P2-09 模板匹配与资源管理

P2-09 可将识别器替换为真实模板识别。

动作侧不需要变化：

```text
识别真实目标 → 坐标映射 → MouseController.click()
```

---

## 18.2 P2-10 自动化任务配置与流程编排

P2-10 可配置：

```text
是否 dry-run
动作后端
点击按钮
点击延迟
点击次数
循环次数
目标模板
```

---

## 18.3 应用配置中心

后续配置中心可管理：

```text
DEFAULT_ACTION_DRY_RUN
动作后端类型
安全校验开关
点击 duration
```

---

# 19. 测试用例清单

## 19.1 模型测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-MODEL-001 | 创建 ActionValidationResult(valid=True) | valid=True |
| TC-P2-08-MODEL-002 | 创建 ActionValidationResult(valid=False) | message 正确 |
| TC-P2-08-MODEL-003 | ClickAction 默认 duration | 50 |
| TC-P2-08-MODEL-004 | ClickAction 默认 button | LEFT |

---

## 19.2 ActionSafetyGuard 测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-SAFE-001 | context=None | valid=False |
| TC-P2-08-SAFE-002 | 点在窗口内部 | valid=True |
| TC-P2-08-SAFE-003 | 点在 left 边界 | valid=True |
| TC-P2-08-SAFE-004 | 点在 top 边界 | valid=True |
| TC-P2-08-SAFE-005 | 点等于 right | valid=False |
| TC-P2-08-SAFE-006 | 点等于 bottom | valid=False |
| TC-P2-08-SAFE-007 | 点在窗口外 | valid=False |
| TC-P2-08-SAFE-008 | 负坐标窗口内点 | valid=True |

---

## 19.3 DryRunMouseBackend 测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-DRY-001 | click | success=True |
| TC-P2-08-DRY-002 | click | 不移动鼠标 |
| TC-P2-08-DRY-003 | click | message 包含 dry-run |
| TC-P2-08-DRY-004 | context=None | 仍 success=True |
| TC-P2-08-DRY-005 | 坐标窗口外 | 仍 success=True |

---

## 19.4 SendInputMouseBackend 安全测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-SEND-001 | context=None | success=False |
| TC-P2-08-SEND-002 | 坐标窗口外 | success=False |
| TC-P2-08-SEND-003 | 坐标窗口内 | 尝试 SetCursorPos |
| TC-P2-08-SEND-004 | SetCursorPos 失败 | success=False |
| TC-P2-08-SEND-005 | SendInput 失败 | success=False |
| TC-P2-08-SEND-006 | SendInput 成功 | success=True |

---

## 19.5 鼠标按钮测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-BTN-001 | LEFT | 使用 LEFTDOWN/LEFTUP |
| TC-P2-08-BTN-002 | RIGHT | 使用 RIGHTDOWN/RIGHTUP |
| TC-P2-08-BTN-003 | MIDDLE | 使用 MIDDLEDOWN/MIDDLEUP |

---

## 19.6 duration 测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-DUR-001 | duration_ms=50 | down/up 间隔约 50ms |
| TC-P2-08-DUR-002 | duration_ms=0 | 立即 up |
| TC-P2-08-DUR-003 | duration_ms<0 | 按 0 处理 |

---

## 19.7 MouseController 测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-CTRL-001 | create_default(True) | 使用 DryRunMouseBackend |
| TC-P2-08-CTRL-002 | create_default(False) | 使用 SendInputMouseBackend |
| TC-P2-08-CTRL-003 | click | 转发给 backend |
| TC-P2-08-CTRL-004 | backend 返回失败 | controller 返回失败 |

---

## 19.8 Worker 集成测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-WORKER-001 | dry_run=True | 默认不真实点击 |
| TC-P2-08-WORKER-002 | dry_run=True | 执行完成 |
| TC-P2-08-WORKER-003 | dry_run=False + 坐标窗口内 | 尝试真实点击 |
| TC-P2-08-WORKER-004 | dry_run=False + 坐标窗口外 | failed |
| TC-P2-08-WORKER-005 | click 返回失败 | Worker failed |
| TC-P2-08-WORKER-006 | click 返回成功 | Worker completed |

---

## 19.9 UI 集成测试

| 编号 | 场景 | 期望 |
|---|---|---|
| TC-P2-08-UI-001 | 默认配置 | MouseController dry-run |
| TC-P2-08-UI-002 | 执行任务 | 日志显示 dry-run |
| TC-P2-08-UI-003 | 临时关闭 dry-run | 使用 SendInput 后端 |
| TC-P2-08-UI-004 | 动作失败 | UI 状态 FAILED |
| TC-P2-08-UI-005 | 动作成功 | UI 状态 COMPLETED |

---

# 20. 验收标准

## 20.1 后端抽象验收

P2-08 完成后应满足：

```text
1. 存在 MouseInputBackend 协议
2. 存在 DryRunMouseBackend
3. 存在 SendInputMouseBackend
4. MouseController 通过 backend 执行动作
5. MouseController 不直接写死 SendInput
6. 后续可扩展其他输入后端
```

---

## 20.2 dry-run 验收

```text
1. DEFAULT_ACTION_DRY_RUN 仍为 True
2. 默认执行任务不真实点击
3. 默认执行任务日志显示 dry-run
4. DryRunMouseBackend 返回 success=True
5. DryRunMouseBackend 不要求 context
```

---

## 20.3 真实点击验收

在临时配置：

```python
DEFAULT_ACTION_DRY_RUN = False
```

或测试注入 `SendInputMouseBackend` 后：

```text
1. 坐标在窗口范围内时尝试真实点击
2. 使用 SetCursorPos 移动鼠标
3. 使用 SendInput 发送 down/up
4. 支持 LEFT / RIGHT / MIDDLE
5. 使用 duration_ms 控制按下时间
6. 成功后返回 ActionResult(success=True)
7. 失败后返回 ActionResult(success=False)
```

---

## 20.4 安全校验验收

```text
1. 存在 ActionSafetyGuard
2. 存在 ActionValidationResult
3. 真实点击前执行安全校验
4. context=None 时拒绝真实点击
5. 坐标超出窗口矩形时拒绝真实点击
6. 坐标在窗口矩形内时允许执行
```

---

## 20.5 Worker 集成验收

```text
1. ExecutorWorker 调用 click(action, context)
2. click success=True 时继续流程
3. click success=False 时 Worker failed
4. dry-run 默认仍可 completed
5. 真实点击失败可显示失败原因
```

---

# 21. 实现顺序建议

建议按以下顺序实现：

```text
1. 检查 ui/config/defaults.py
2. 确认 DEFAULT_ACTION_DRY_RUN = True

3. 修改 nzfz_executor/core/actions/models.py
4. 新增 ActionValidationResult

5. 新建 nzfz_executor/core/actions/safety.py
6. 实现 ActionSafetyGuard

7. 新建 nzfz_executor/core/actions/backends/__init__.py
8. 新建 nzfz_executor/core/actions/backends/base.py
9. 实现 MouseInputBackend

10. 新建 nzfz_executor/core/actions/backends/dry_run_backend.py
11. 实现 DryRunMouseBackend

12. 新建 nzfz_executor/core/actions/backends/send_input_backend.py
13. 实现 SendInputMouseBackend
14. 实现 SetCursorPos
15. 实现 SendInput down/up
16. 实现按钮映射
17. 实现 duration_ms

18. 修改 nzfz_executor/core/actions/mouse_controller.py
19. 改为 backend 组合
20. 增加 create_default(dry_run)

21. 修改 ui/workers/executor_workers.py
22. 将 mouse_controller.click(action) 改为 click(action, context)

23. 修改 ui/tabs/game_connect.py
24. 将 MouseController(...) 改为 MouseController.create_default(...)

25. 手动测试默认 dry-run
26. 单元测试 safety guard
27. 单元测试 dry-run backend
28. 谨慎测试 SendInput 后端
```

---

# 22. 最终结论

P2-08 的核心目标是：

```text
将 P2-07 中的动作 dry-run 骨架升级为可扩展的 Windows 输入动作后端。
```

本阶段新增：

```text
MouseInputBackend
DryRunMouseBackend
SendInputMouseBackend
ActionSafetyGuard
ActionValidationResult
MouseController backend 组合模式
```

并实现：

```text
SetCursorPos + SendInput down/up
```

用于真实点击。

但为了安全，P2-08 明确保持：

```python
DEFAULT_ACTION_DRY_RUN = True
```

因此默认执行仍然不会真实点击。

P2-08 完成后，系统将同时具备：

```text
安全默认 dry-run
可测试真实点击
可扩展输入后端
真实点击前安全校验
动作失败反馈
```

这为后续：

```text
P2-09 模板匹配与资源管理
P2-10 自动化任务配置与流程编排
P2-xx 应用配置中心与用户设置
```

提供了稳定的动作执行基础。
