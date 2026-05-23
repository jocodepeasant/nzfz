# P0-04 真实 Windows 窗口连接前校验详细设计文档

文档版本：`v1.1`  
适用模块：

```text
nzfz_executor/core/window_manager.py
```

关联模型：

```text
nzfz_executor/core/models.py
```

适用需求：

```text
P0-04 真实 Windows 窗口连接前校验
```

前置依赖：

```text
P0-01 窗口连接数据模型
P0-02 WindowManager 基础类
P0-03 真实 Windows 窗口搜索
```

后续依赖：

```text
P0-05 连接窗口上下文构建
P0-06 连接成功前激活目标窗口
```

---

## 1. 版本说明

### 1.1 v1.1 修订目标

本文档用于定义 `WindowManager.connect_window()` 中的**连接前校验阶段**。

P0-04 的职责是：

```text
基于 P0-03 搜索得到的 WindowInfo，在连接前重新验证目标窗口当前是否仍然具备连接资格。
```

P0-04 不负责构建 `ConnectedWindow`，不负责保存 `_connected_window`，不负责实现窗口激活算法。

本阶段校验通过后，连接流程才允许进入：

```text
P0-05 连接窗口上下文构建
P0-06 连接成功前激活目标窗口
```

---

## 2. 与整体连接流程的关系

完整 `connect_window()` 推荐流程如下：

```text
1. 接收 WindowInfo 与 ConnectOptions
2. P0-04：连接前校验
3. P0-05：构建 ConnectedWindow 候选对象
4. P0-06：激活目标窗口
5. 所有步骤成功后保存 _connected_window
6. 返回 ConnectResult.success
```

P0-04 只覆盖第 1、2 步。

---

## 3. 设计目标

P0-04 的目标是在连接前确认：

- 当前运行平台是否支持；
- Windows API 依赖是否可用；
- 输入的 `WindowInfo` 是否合法；
- `hwnd` 是否仍然有效；
- 当前窗口 PID 是否仍与搜索结果一致；
- 目标进程是否仍然存活；
- 当前进程名是否可以获取；
- 目标窗口是否可见；
- 目标窗口是否未最小化；
- 当前窗口标题是否可以获取且不为空；
- 当前版本中被忽略的 `ConnectOptions` 是否记录日志；
- 校验失败时返回明确错误；
- 校验失败时不清空旧连接。

---

## 4. 设计结论

| 项目                         | 最终选择                                                  |
| ---------------------------- | --------------------------------------------------------- |
| 实现位置                     | `nzfz_executor/core/window_manager.py`                    |
| 对外接口                     | 复用 `WindowManager.connect_window(window, options=None)` |
| 入参来源                     | P0-03 搜索得到的 `WindowInfo`                             |
| 返回类型                     | `ConnectResult`                                           |
| 本阶段职责                   | 连接前校验                                                |
| 是否构建 `ConnectedWindow`   | 否                                                        |
| 是否保存 `_connected_window` | 否                                                        |
| 是否激活窗口                 | 否，仅要求后续流程必须调用 P0-06                          |
| 是否信任搜索快照             | 否                                                        |
| 非 Windows 行为              | 返回失败，并写入 `_last_error`                            |
| 缺少依赖行为                 | 返回失败，并写入 `_last_error`                            |
| `window is None`             | 返回失败                                                  |
| `hwnd <= 0`                  | 返回失败                                                  |
| `pid <= 0`                   | 返回失败                                                  |
| `hwnd` 校验                  | 调用 `win32gui.IsWindow(hwnd)`                            |
| PID 获取                     | 调用 `win32process.GetWindowThreadProcessId(hwnd)`        |
| PID 一致性                   | 当前 PID 必须等于 `WindowInfo.pid`                        |
| 进程存活校验                 | 使用 `psutil.Process(pid).is_running()`                   |
| 进程名                       | 必须可获取                                                |
| 标题                         | 必须重新获取，允许变化，但不能为空                        |
| 可见性                       | 不允许连接不可见窗口                                      |
| 最小化窗口                   | 不允许连接                                                |
| `restore_if_minimized=True`  | 当前版本忽略，不自动恢复，仅记录日志                      |
| `activate_on_connect=False`  | 当前版本忽略，后续仍强制激活，仅记录日志                  |
| `control_mode=BACKGROUND`    | 当前版本忽略，仍按前台连接处理，仅记录日志                |
| 失败状态策略                 | 只更新 `_last_error`，不清空旧连接                        |
| 日志                         | 使用 `logging.getLogger(__name__)`                        |

---

## 5. 模块边界

### 5.1 P0-04 负责内容

P0-04 负责：

- 接收 `WindowInfo`；
- 处理默认 `ConnectOptions`；
- 检查运行平台；
- 检查依赖可用性；
- 校验 `window` 入参；
- 校验 `hwnd` 是否为正整数；
- 校验 `pid` 是否为正整数；
- 校验 `hwnd` 是否仍然有效；
- 获取当前窗口 PID；
- 校验当前 PID 是否与 `WindowInfo.pid` 一致；
- 校验目标进程是否仍然存活；
- 获取当前进程名；
- 校验窗口是否可见；
- 校验窗口是否最小化；
- 拒绝连接最小化窗口；
- 获取当前窗口标题；
- 校验当前窗口标题非空；
- 对当前版本暂不支持的 `ConnectOptions` 记录日志；
- 返回连接前校验结果；
- 失败时写入 `_last_error`；
- 失败时不清空 `_connected_window`。

### 5.2 P0-04 不负责内容

P0-04 不负责：

- 搜索窗口；
- 获取窗口矩形；
- 获取客户区矩形；
- 校验窗口矩形尺寸；
- 校验客户区矩形尺寸；
- 构建 `ConnectedWindow`；
- 保存 `_connected_window`；
- 保存 `_last_window_info`；
- 激活目标窗口；
- 实现 `_activate_window()`；
- 自动恢复最小化窗口；
- 后台输入；
- 后台消息控制；
- 截图；
- 图像识别；
- 自动点击；
- 自动重连；
- 多窗口会话管理；
- 健康检测；
- GUI 线程控制；
- GUI 超时控制。

---

## 6. 核心语义

### 6.1 `WindowInfo` 是搜索快照

P0-03 返回的 `WindowInfo` 只代表搜索时刻的窗口状态。

它不保证：

- `hwnd` 当前仍有效；
- PID 当前仍一致；
- 进程当前仍存活；
- 窗口当前仍可见；
- 窗口当前未最小化；
- 标题当前未变化；
- 标题当前非空。

因此 P0-04 必须重新校验当前真实状态。

### 6.2 连接前校验不产生连接状态

P0-04 校验通过仅表示：

```text
目标窗口当前可以进入后续连接流程。
```

不表示连接已经成功。

因此 P0-04 不允许写入：

```python
self._connected_window
```

也不允许覆盖：

```python
self._last_window_info
```

### 6.3 失败不影响旧连接

如果当前已有旧连接，新连接校验失败时：

- 不清空 `_connected_window`；
- 不清空 `_last_window_info`；
- 只更新 `_last_error`；
- 返回 `ConnectResult.fail(error_message)`。

---

## 7. 对外接口设计

### 7.1 公开方法

P0-04 继续复用 P0-02 已定义接口：

```python
def connect_window(
    self,
    window: WindowInfo,
    options: Optional[ConnectOptions] = None,
) -> ConnectResult:
    ...
```

P0-04 是该方法内部的第一阶段。

### 7.2 推荐私有方法

建议新增私有方法：

```python
def _validate_window_for_connect(
    self,
    window: WindowInfo,
    options: ConnectOptions,
) -> tuple[bool, str]:
    ...
```

返回：

| 返回值 | 说明                       |
| ------ | -------------------------- |
| `bool` | 是否校验通过               |
| `str`  | 失败原因，成功时为空字符串 |

---

## 8. 校验流程

### 8.1 标准流程

推荐顺序：

```text
1. options 默认化
2. 记录当前版本不支持的 options 配置
3. 校验运行平台
4. 校验依赖
5. 校验 window is not None
6. 校验 window.hwnd > 0
7. 校验 window.pid > 0
8. 调用 IsWindow(hwnd)
9. 调用 GetWindowThreadProcessId(hwnd)
10. 校验当前 PID 与 window.pid 一致
11. 使用 psutil.Process(pid) 获取进程对象
12. 校验进程 is_running()
13. 获取进程名 process.name()
14. 调用 IsWindowVisible(hwnd)
15. 调用 IsIconic(hwnd)
16. 调用 GetWindowText(hwnd)
17. 校验标题非空
18. 返回校验通过
```

### 8.2 最小化窗口处理

连接阶段禁止连接最小化窗口。

即使调用方传入：

```python
ConnectOptions(restore_if_minimized=True)
```

当前版本仍不自动恢复窗口。

失败信息建议为：

```text
连接失败：窗口已最小化，请恢复窗口后重试
```

### 8.3 不支持选项日志

当前版本中以下选项不改变实际行为：

- `restore_if_minimized=True`
- `activate_on_connect=False`
- `control_mode != ControlMode.FOREGROUND`

建议记录日志：

```python
if options.restore_if_minimized:
    logger.info("当前版本暂不支持自动恢复最小化窗口")

if not options.activate_on_connect:
    logger.info("当前版本暂不支持跳过窗口激活，仍会尝试激活目标窗口")

if options.control_mode != ControlMode.FOREGROUND:
    logger.info(
        "当前版本暂不支持非前台控制，仍按 FOREGROUND 流程连接: mode=%s",
        options.control_mode,
    )
```

---

## 9. 错误处理设计

### 9.1 失败错误信息

| 场景                       | 错误信息建议                               |
| -------------------------- | ------------------------------------------ |
| 非 Windows 平台            | `连接失败：当前平台不支持真实窗口连接`     |
| 缺少 pywin32               | `连接失败：缺少 pywin32 依赖`              |
| 缺少 psutil                | `连接失败：缺少 psutil 依赖`               |
| `window is None`           | `连接失败：窗口信息为空`                   |
| `hwnd <= 0`                | `连接失败：窗口句柄无效`                   |
| `pid <= 0`                 | `连接失败：窗口 PID 无效`                  |
| `IsWindow(hwnd)` 为假      | `连接失败：窗口句柄已失效，请重新搜索`     |
| 当前 PID 与搜索 PID 不一致 | `连接失败：窗口进程已变化，请重新搜索`     |
| 进程不存在                 | `连接失败：目标进程不存在`                 |
| 进程不可访问               | `连接失败：无法访问目标进程信息`           |
| 进程未运行                 | `连接失败：目标进程未运行`                 |
| 进程名获取失败             | `连接失败：无法获取目标进程名称`           |
| 窗口不可见                 | `连接失败：窗口不可见`                     |
| 窗口已最小化               | `连接失败：窗口已最小化，请恢复窗口后重试` |
| 标题为空                   | `连接失败：窗口标题为空，请重新搜索`       |
| 未知异常                   | `连接失败：连接前校验异常：{exception}`    |

### 9.2 `psutil` 异常处理

必须处理：

```python
psutil.NoSuchProcess
psutil.AccessDenied
psutil.ZombieProcess
```

建议策略：

| 异常            | 策略                   |
| --------------- | ---------------------- |
| `NoSuchProcess` | 连接失败               |
| `AccessDenied`  | 连接失败               |
| `ZombieProcess` | 连接失败               |
| 其他异常        | 连接失败，写入异常信息 |

---

## 10. 推荐伪代码

```python
def _validate_window_for_connect(
    self,
    window: WindowInfo,
    options: ConnectOptions,
) -> tuple[bool, str]:
    try:
        self._log_unsupported_options(options)

        if not self._is_windows:
            return False, "连接失败：当前平台不支持真实窗口连接"

        if not self._win32_available:
            return False, "连接失败：缺少 pywin32 依赖"

        if not self._psutil_available:
            return False, "连接失败：缺少 psutil 依赖"

        if window is None:
            return False, "连接失败：窗口信息为空"

        hwnd = window.hwnd
        expected_pid = window.pid

        if hwnd <= 0:
            return False, "连接失败：窗口句柄无效"

        if expected_pid <= 0:
            return False, "连接失败：窗口 PID 无效"

        if not win32gui.IsWindow(hwnd):
            return False, "连接失败：窗口句柄已失效，请重新搜索"

        _, current_pid = win32process.GetWindowThreadProcessId(hwnd)
        if current_pid != expected_pid:
            return False, "连接失败：窗口进程已变化，请重新搜索"

        try:
            process = psutil.Process(current_pid)
            if not process.is_running():
                return False, "连接失败：目标进程未运行"

            process_name = process.name()
            if not process_name:
                return False, "连接失败：无法获取目标进程名称"

        except psutil.NoSuchProcess:
            return False, "连接失败：目标进程不存在"
        except psutil.AccessDenied:
            return False, "连接失败：无法访问目标进程信息"
        except psutil.ZombieProcess:
            return False, "连接失败：目标进程状态异常"

        if not win32gui.IsWindowVisible(hwnd):
            return False, "连接失败：窗口不可见"

        if win32gui.IsIconic(hwnd):
            return False, "连接失败：窗口已最小化，请恢复窗口后重试"

        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return False, "连接失败：窗口标题为空，请重新搜索"

        return True, ""

    except Exception as exc:
        logger.exception("连接前校验异常")
        return False, f"连接失败：连接前校验异常：{exc}"
```

---

## 11. 验收标准

- [ ] 非 Windows 平台连接失败；
- [ ] 缺少依赖时连接失败；
- [ ] `window is None` 时连接失败；
- [ ] `hwnd <= 0` 时连接失败；
- [ ] `pid <= 0` 时连接失败；
- [ ] `hwnd` 失效时连接失败；
- [ ] 当前 PID 与搜索 PID 不一致时连接失败；
- [ ] 目标进程不存在时连接失败；
- [ ] 目标进程不可访问时连接失败；
- [ ] 目标窗口不可见时连接失败；
- [ ] 目标窗口最小化时连接失败；
- [ ] 当前标题为空时连接失败；
- [ ] `restore_if_minimized=True` 不自动恢复窗口；
- [ ] `activate_on_connect=False` 不跳过后续激活；
- [ ] `control_mode=BACKGROUND` 当前仍按前台流程处理；
- [ ] 任意失败不清空旧连接；
- [ ] 任意失败写入 `_last_error`；
- [ ] 校验通过后不写入 `_connected_window`。