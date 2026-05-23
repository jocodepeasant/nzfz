# P0-03 真实 Windows 窗口搜索详细设计文档

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
P0-03 真实 Windows 窗口搜索
```

前置依赖：

```text
P0-01 窗口连接数据模型
P0-02 WindowManager 基础类
```

---

## 1. 版本说明

### 1.1 v1.1 修订内容

相比 v1.0，本版本主要修订以下内容：

| 修订项 | 说明 |
|---|---|
| 空关键词处理顺序 | 改为先处理空关键词，再检查平台和依赖 |
| 最小化窗口搜索策略 | 搜索阶段允许返回最小化窗口 |
| 最小化窗口尺寸来源 | 最小化窗口使用 `GetWindowPlacement().rcNormalPosition` 计算恢复后尺寸 |
| 连接边界 | 搜索可返回最小化窗口，但 P0-04 连接阶段仍禁止连接最小化窗口 |
| `_last_window_info` 语义 | 明确 `search_windows()` 不更新 `_last_window_info` |
| `_last_error` 语义 | 明确空关键词、成功搜索、单窗口异常、整体异常时的处理规则 |
| 测试章节 | 修正空关键词测试，使其不依赖 Windows 平台 |
| 边界说明 | 明确不做模糊匹配、不做去重、不做自动恢复、不连接窗口 |

---

## 2. 设计目标

P0-03 的目标是在 `WindowManager.search_windows(keyword)` 中实现真实 Windows 顶层窗口搜索能力。

本阶段完成后，执行器 Core 层应能够根据用户输入关键词，搜索当前 Windows 系统中的可见顶层窗口，并返回符合条件的 `WindowInfo` 列表。

支持搜索范围：

```text
窗口标题
进程名
PID
```

搜索结果必须包含：

```text
hwnd
title
process_name
pid
width
height
match_score
is_visible
is_minimized
```

搜索结果必须按：

```text
match_score 降序
```

排列。

---

## 3. 设计结论

根据当前需求文档、拆分文档和 P0-01/P0-02 已完成设计，P0-03 最终采用以下方案：

| 项目 | 最终选择 |
|---|---|
| 实现位置 | `nzfz_executor/core/window_manager.py` |
| 对外接口 | 复用 `WindowManager.search_windows(keyword)` |
| 返回类型 | `list[WindowInfo]` |
| Windows API | `win32gui.EnumWindows`、`win32gui.IsWindow`、`win32gui.IsWindowVisible`、`win32gui.GetWindowText`、`win32gui.GetWindowRect`、`win32gui.GetWindowPlacement`、`win32gui.IsIconic` |
| 进程 API | `win32process.GetWindowThreadProcessId` |
| 进程信息 | `psutil.Process(pid).name()` |
| 空关键词行为 | 直接返回空列表，清空 `_last_error`，不检查平台 |
| 非 Windows 行为 | 返回空列表，并写入 `_last_error` |
| 缺少依赖行为 | 返回空列表，并写入 `_last_error` |
| 单窗口异常 | 捕获异常，跳过该窗口，不影响整体搜索 |
| 整体异常 | 捕获异常，记录 `_last_error`，返回当前已收集结果 |
| 匹配范围 | 标题、进程名、PID |
| PID 匹配 | 仅当关键词为数字时进行精确匹配 |
| 搜索过滤 | 只保留有效、可见、有标题、尺寸合规、可获取 PID 和进程名的窗口 |
| 最小化窗口 | 搜索阶段允许返回，通过 `WindowInfo.is_minimized=True` 标记 |
| 最小化窗口尺寸 | 使用 `GetWindowPlacement(hwnd)` 的 `rcNormalPosition` 计算恢复后尺寸 |
| 连接最小化窗口 | P0-03 不负责；P0-04 仍禁止连接当前最小化窗口 |
| 排序规则 | `match_score` 降序，分数相同保持枚举顺序 |
| 去重策略 | 不按标题、PID、进程名去重；每个 `hwnd` 代表独立窗口候选 |
| GUI 依赖 | GUI 只消费 `WindowInfo`，不直接调用 Windows API |

---

## 4. 模块边界

### 4.1 P0-03 负责内容

P0-03 只负责真实窗口搜索，包括：

- 清理关键词；
- 空关键词直接返回；
- 检查平台是否支持；
- 检查依赖是否可用；
- 枚举 Windows 顶层窗口；
- 过滤无效窗口；
- 获取窗口标题；
- 获取窗口 PID；
- 获取进程名；
- 判断窗口是否可见；
- 判断窗口是否最小化；
- 获取搜索阶段使用的窗口矩形；
- 对非最小化窗口使用 `GetWindowRect`；
- 对最小化窗口使用 `GetWindowPlacement().rcNormalPosition`；
- 计算匹配分数；
- 构造 `WindowInfo`；
- 按匹配分数排序；
- 返回搜索结果；
- 记录基础日志。

---

### 4.2 P0-03 不负责内容

P0-03 不实现以下能力：

- 连接窗口；
- 激活窗口；
- 自动恢复最小化窗口；
- 保存 `ConnectedWindow`；
- 获取客户区矩形；
- 健康检测；
- GUI 表格渲染；
- 连接按钮状态控制；
- 子线程连接；
- 连接超时；
- 截图；
- 图像识别；
- 自动点击；
- 后台输入；
- 自动重连；
- 多窗口会话管理；
- 模糊匹配；
- 拼音匹配；
- 正则匹配；
- 多关键词分词匹配；
- 繁简转换；
- 进程路径匹配。

---

## 5. 对外接口设计

### 5.1 方法签名

P0-03 继续使用 P0-02 已定义的公开接口：

```python
def search_windows(self, keyword: str) -> list[WindowInfo]:
    ...
```

---

### 5.2 方法语义

```python
def search_windows(self, keyword: str) -> list[WindowInfo]:
    """
    搜索匹配关键词的可见 Windows 顶层窗口。

    匹配范围：
    - 窗口标题
    - 进程名称
    - PID

    Args:
        keyword: 用户输入的搜索关键词。

    Returns:
        匹配的 WindowInfo 列表，按 match_score 降序排列。
    """
```

---

### 5.3 入参说明

| 参数 | 类型 | 说明 |
|---|---|---|
| `keyword` | `str` | 用户输入的搜索关键词 |

入参处理规则：

```text
1. 如果 keyword 为 None，按空字符串处理；
2. 去除 keyword 前后空白字符；
3. 如果清理后为空，直接返回空列表；
4. 空关键词不检查平台；
5. 空关键词不视为错误；
6. 不修改用户输入的大小写展示，只在匹配时转为小写。
```

推荐实现：

```python
keyword = (keyword or "").strip()
if not keyword:
    self._last_error = ""
    return []
```

---

### 5.4 返回值说明

返回：

```python
list[WindowInfo]
```

每个 `WindowInfo` 表示搜索时刻的窗口快照。

注意：

```text
WindowInfo 只是搜索结果快照，不代表窗口在连接时仍然有效。
```

连接时必须在 P0-04 中重新校验：

- `hwnd` 是否有效；
- PID 是否存活；
- hwnd 当前 PID 是否仍一致；
- 窗口是否可见；
- 窗口是否最小化；
- 窗口尺寸是否有效。

---

## 6. 搜索流程设计

### 6.1 总体流程

```text
1. 清理 keyword
2. keyword 为空则清空 _last_error 并返回空列表
3. 检查运行环境是否支持
4. 不支持则写入 _last_error 并返回空列表
5. 初始化结果列表
6. 调用 win32gui.EnumWindows 枚举所有顶层窗口
7. 对每个 hwnd 执行单窗口处理
8. 单窗口处理过程中进行基础过滤
9. 获取窗口标题
10. 判断窗口是否最小化
11. 获取搜索用窗口矩形
    - 未最小化：GetWindowRect
    - 已最小化：GetWindowPlacement().rcNormalPosition
12. 获取窗口 PID
13. 获取进程名
14. 计算匹配分数
15. 分数大于 0 才加入结果
16. 按 match_score 降序排序
17. 搜索成功后清空 _last_error
18. 记录日志
19. 返回结果
```

---

### 6.2 流程图

```text
search_windows(keyword)
    ↓
清理 keyword
    ↓
keyword 为空？
    ├─ 是 → _last_error = "" → return []
    └─ 否
        ↓
_ensure_supported()
    ↓
不支持？
    ├─ 是 → _last_error = reason → return []
    └─ 否
        ↓
win32gui.EnumWindows(callback)
    ↓
callback(hwnd)
    ↓
_build_window_info_if_match(hwnd, keyword)
    ↓
返回 WindowInfo 或 None
    ↓
加入 results
    ↓
results.sort(match_score desc)
    ↓
_last_error = ""
    ↓
return results
```

---

## 7. 窗口基础过滤规则

枚举窗口时，默认过滤掉以下窗口：

| 条件 | 处理 |
|---|---|
| 不是有效窗口 | 跳过 |
| 不可见窗口 | 跳过 |
| 无标题窗口 | 跳过 |
| 获取搜索用窗口矩形失败 | 跳过 |
| 非最小化窗口宽度小于 `200` | 跳过 |
| 非最小化窗口高度小于 `150` | 跳过 |
| 最小化窗口恢复矩形宽度小于 `200` | 跳过 |
| 最小化窗口恢复矩形高度小于 `150` | 跳过 |
| 获取 PID 失败 | 跳过 |
| PID 小于等于 `0` | 跳过 |
| 获取进程名失败 | 跳过 |
| 进程名为空 | 跳过 |
| 匹配分数为 `0` | 跳过 |

---

### 7.1 尺寸过滤常量

建议在 `WindowManager` 中定义类常量：

```python
MIN_WINDOW_WIDTH = 200
MIN_WINDOW_HEIGHT = 150
```

用于搜索阶段过滤明显无效或非目标窗口。

---

### 7.2 有效窗口检查

```python
if not win32gui.IsWindow(hwnd):
    return None
```

---

### 7.3 可见窗口检查

```python
is_visible = bool(win32gui.IsWindowVisible(hwnd))
if not is_visible:
    return None
```

说明：

```text
P0-03 默认只搜索可见窗口。
可见窗口不代表未最小化。
最小化窗口仍可能被视为可见。
```

---

### 7.4 窗口标题检查

```python
title = win32gui.GetWindowText(hwnd).strip()
if not title:
    return None
```

说明：

```text
无标题窗口通常不是用户可选择的游戏窗口，搜索阶段直接过滤。
```

---

### 7.5 最小化状态检查

搜索阶段需要判断窗口是否最小化：

```python
is_minimized = bool(win32gui.IsIconic(hwnd))
```

P0-03 搜索阶段允许最小化窗口进入结果列表，但必须在 `WindowInfo` 中标记：

```python
is_minimized=True
```

注意：

```text
搜索到最小化窗口不代表可以直接连接。
P0-04 连接阶段仍需要重新检查窗口当前是否最小化。
如果连接时窗口仍最小化，应返回连接失败。
```

---

## 8. 搜索用窗口矩形设计

### 8.1 设计背景

P0-03 搜索结果中的 `WindowInfo` 需要包含：

```text
width
height
```

对于普通窗口，可以直接使用：

```python
win32gui.GetWindowRect(hwnd)
```

但对于最小化窗口，`GetWindowRect(hwnd)` 的返回值可能不是用户预期的窗口正常尺寸，可能出现：

```text
负坐标
异常位置
异常尺寸
历史位置
```

因此，对于最小化窗口，搜索阶段应优先使用：

```python
win32gui.GetWindowPlacement(hwnd)
```

返回结果中的：

```text
rcNormalPosition
```

作为窗口恢复后的矩形。

---

### 8.2 非最小化窗口矩形

非最小化窗口使用：

```python
left, top, right, bottom = win32gui.GetWindowRect(hwnd)
```

然后构造：

```python
WindowRect(left, top, right, bottom)
```

---

### 8.3 最小化窗口矩形

最小化窗口使用：

```python
placement = win32gui.GetWindowPlacement(hwnd)
rc_normal = placement[4]
left, top, right, bottom = rc_normal
```

然后构造：

```python
WindowRect(left, top, right, bottom)
```

说明：

```text
rcNormalPosition 表示窗口恢复后的正常位置。
它比最小化状态下的 GetWindowRect 更适合用于搜索结果中的 width / height。
```

---

### 8.4 搜索矩形获取方法

建议新增私有方法：

```python
def _get_search_window_rect(
    self,
    hwnd: int,
    is_minimized: bool,
) -> Optional[WindowRect]:
    ...
```

该方法只用于 P0-03 搜索阶段，不等同于 P0-05 连接阶段的窗口矩形获取。

P0-05 连接阶段仍应在窗口非最小化的前提下，重新调用：

```python
win32gui.GetWindowRect(hwnd)
```

获取真实当前窗口矩形。

---

### 8.5 矩形有效性校验

无论是否最小化，搜索阶段矩形都必须满足：

```python
rect.is_valid(
    min_width=self.MIN_WINDOW_WIDTH,
    min_height=self.MIN_WINDOW_HEIGHT,
)
```

如果不满足，则跳过该窗口。

---

## 9. PID 与进程名获取

### 9.1 PID 获取

```python
_, pid = win32process.GetWindowThreadProcessId(hwnd)
if pid <= 0:
    return None
```

---

### 9.2 进程名获取

```python
process_name = psutil.Process(pid).name()
if not process_name:
    return None
```

可能异常：

- `psutil.NoSuchProcess`
- `psutil.AccessDenied`
- `psutil.ZombieProcess`
- 其他运行时异常

处理策略：

```text
单个窗口获取进程名失败时跳过该窗口，不中断整个搜索。
```

权限说明：

```text
如果因为权限不足导致目标游戏搜索不到，建议用户尝试以管理员身份运行工具。
P0-03 不在搜索结果中加入无法获取进程名的窗口，因为 WindowInfo 必须包含 process_name。
```

---

## 10. 匹配规则设计

### 10.1 匹配范围

关键词匹配以下内容：

| 匹配对象 | 匹配方式 |
|---|---|
| 窗口标题 | 忽略大小写，包含匹配 |
| 进程名 | 忽略大小写，包含匹配 |
| PID | 仅数字关键词，精确匹配 |

---

### 10.2 当前不支持的匹配能力

P0-03 当前不实现：

- 拼音匹配；
- 编辑距离匹配；
- 正则匹配；
- 多关键词拆分；
- 空格分词；
- 繁简转换；
- 进程路径匹配；
- 窗口类名匹配。

---

### 10.3 匹配分数规则

使用需求文档中规定的匹配度规则：

```python
@staticmethod
def _calculate_match_score(
    keyword: str,
    title: str,
    process_name: str,
    pid: int,
) -> float:
    keyword = (keyword or "").lower().strip()
    title_lower = (title or "").lower()
    process_lower = (process_name or "").lower()

    if not keyword:
        return 0.0

    if keyword.isdigit():
        try:
            if int(keyword) == pid:
                return 1.0
        except ValueError:
            pass

    if title_lower == keyword:
        return 1.0

    if process_lower == keyword:
        return 0.95

    if keyword in title_lower:
        return 0.85

    if keyword in process_lower:
        return 0.8

    return 0.0
```

---

### 10.4 匹配优先级

匹配优先级从高到低：

| 优先级 | 条件 | 分数 |
|---:|---|---:|
| 1 | PID 精确匹配 | `1.0` |
| 2 | 标题完全匹配 | `1.0` |
| 3 | 进程名完全匹配 | `0.95` |
| 4 | 标题包含关键词 | `0.85` |
| 5 | 进程名包含关键词 | `0.8` |
| 6 | 不匹配 | `0.0` |

---

## 11. 搜索结果排序设计

### 11.1 排序规则

搜索结果必须按：

```python
match_score
```

降序排序。

推荐实现：

```python
results.sort(key=lambda item: item.match_score, reverse=True)
```

---

### 11.2 同分处理

当前版本同分时：

```text
保持 Windows 枚举顺序。
```

原因：

1. 实现简单；
2. 不引入额外排序规则；
3. 与需求中“可按窗口标题升序或保持枚举顺序”一致；
4. Python 排序是稳定排序，相同分数会保持原有顺序。

---

### 11.3 去重策略

P0-03 不按以下字段去重：

- 标题；
- PID；
- 进程名；
- 标题 + PID；
- 进程名 + PID。

原因：

```text
hwnd 才是窗口连接的核心标识。
多个窗口可能属于同一个进程。
同一个程序可能有多个顶层窗口。
多开游戏时可能出现相同标题或相同进程名的多个窗口。
```

因此：

```text
每个 hwnd 代表一个独立窗口候选。
```

---

## 12. 最小化窗口处理策略

### 12.1 搜索阶段

P0-03 搜索阶段允许返回最小化窗口。

当窗口最小化时：

```python
is_minimized = True
```

搜索结果中的 `WindowInfo` 应设置：

```python
WindowInfo(
    ...
    is_minimized=True,
)
```

---

### 12.2 最小化窗口尺寸来源

最小化窗口不直接使用 `GetWindowRect(hwnd)` 计算搜索结果尺寸，而是使用：

```python
win32gui.GetWindowPlacement(hwnd)
```

返回值中的：

```text
rcNormalPosition
```

作为窗口恢复后的矩形。

---

### 12.3 连接阶段边界

搜索支持最小化窗口，不代表连接支持最小化窗口。

P0-04 连接阶段仍必须重新检查：

```python
win32gui.IsIconic(window.hwnd)
```

如果连接时窗口仍然最小化，应返回：

```python
ConnectResult.fail("窗口已最小化，请恢复窗口后重试")
```

场景示例：

```text
1. 用户搜索到最小化窗口；
2. 搜索结果中 is_minimized=True；
3. 用户手动恢复窗口；
4. 点击连接；
5. P0-04 重新检查窗口当前状态；
6. 如果当前已经不是最小化，则可以继续连接流程。
```

---

### 12.4 当前版本不自动恢复窗口

P0-03 不执行：

```python
win32gui.ShowWindow(hwnd, ...)
```

P0-04 当前版本也不应因为：

```python
ConnectOptions.restore_if_minimized=True
```

而自动恢复窗口。

自动恢复最小化窗口属于后续增强能力，不进入当前 P0 范围。

---

## 13. 私有方法设计

为避免 `search_windows()` 过长，建议在 `WindowManager` 中增加以下私有方法。

---

### 13.1 `_calculate_match_score()`

#### 方法签名

```python
@staticmethod
def _calculate_match_score(
    keyword: str,
    title: str,
    process_name: str,
    pid: int,
) -> float:
    ...
```

#### 职责

负责根据关键词、标题、进程名和 PID 计算匹配分数。

#### 返回

```text
0.0 ~ 1.0
```

如果返回 `0.0`，表示不匹配，不加入搜索结果。

---

### 13.2 `_build_window_info_if_match()`

#### 方法签名

```python
def _build_window_info_if_match(
    self,
    hwnd: int,
    keyword: str,
) -> Optional[WindowInfo]:
    ...
```

#### 职责

负责处理单个 hwnd：

1. 校验 hwnd；
2. 判断可见性；
3. 获取标题；
4. 判断是否最小化；
5. 获取搜索用窗口矩形；
6. 获取 PID；
7. 获取进程名；
8. 计算匹配分数；
9. 构造并返回 `WindowInfo`。

如果该窗口不符合条件或发生异常，则返回：

```python
None
```

---

### 13.3 `_get_search_window_rect()`

#### 方法签名

```python
def _get_search_window_rect(
    self,
    hwnd: int,
    is_minimized: bool,
) -> Optional[WindowRect]:
    ...
```

#### 职责

根据窗口最小化状态获取搜索阶段使用的窗口矩形。

规则：

| 状态 | 矩形来源 |
|---|---|
| 非最小化 | `win32gui.GetWindowRect(hwnd)` |
| 最小化 | `win32gui.GetWindowPlacement(hwnd)` 的 `rcNormalPosition` |

#### 返回

| 情况 | 返回 |
|---|---|
| 获取成功且尺寸有效 | `WindowRect` |
| 获取失败 | `None` |
| 尺寸无效 | `None` |

---

### 13.4 `_get_process_name()`

#### 方法签名

```python
def _get_process_name(self, pid: int) -> Optional[str]:
    ...
```

#### 职责

根据 PID 获取进程名。

#### 返回

| 情况 | 返回 |
|---|---|
| 获取成功 | 进程名字符串 |
| 进程不存在 | `None` |
| 权限不足 | `None` |
| 其他异常 | `None` |

#### 说明

搜索阶段不因为单个进程名获取失败而报错给 UI。

---

## 14. 状态字段更新规则

### 14.1 `_last_error`

P0-03 中 `_last_error` 的更新规则如下：

| 场景 | `_last_error` |
|---|---|
| 空关键词 | 清空为 `""` |
| 平台不支持 | 设置为不支持原因 |
| 缺少依赖 | 设置为依赖缺失原因 |
| 搜索成功 | 清空为 `""` |
| 搜索无结果但无异常 | 清空为 `""` |
| 单个窗口处理异常 | 不修改 |
| 整体搜索异常 | 设置为异常详情 |

说明：

```text
单个窗口异常不代表搜索失败，因此不写入 _last_error。
```

---

### 14.2 `_last_window_info`

P0-03 中 `search_windows()` 不更新：

```python
self._last_window_info
```

原因：

```text
_last_window_info 表示最近一次连接使用的搜索结果。
它不表示最近一次搜索结果。
```

`_last_window_info` 只应在后续 P0-07 连接成功或连接流程中按设计更新。

---

### 14.3 `_connected_window`

P0-03 中 `search_windows()` 不更新：

```python
self._connected_window
```

搜索窗口不代表连接窗口。

---

## 15. 日志设计

P0-03 建议补充基础日志。

### 15.1 搜索开始

```python
logger.info("开始搜索窗口，关键词：%s", keyword)
```

---

### 15.2 搜索完成

```python
logger.info("搜索窗口完成，结果数量：%s", len(results))
```

---

### 15.3 单窗口异常

单窗口异常建议使用 `debug` 级别，避免普通用户日志过多：

```python
logger.debug("处理窗口失败，hwnd=%s，错误：%s", hwnd, exc)
```

---

### 15.4 整体搜索异常

整体搜索异常使用 `error`：

```python
logger.exception("搜索窗口时发生未知异常")
```

同时更新：

```python
self._last_error = str(exc)
```

---

## 16. 异常处理策略

### 16.1 空关键词

空关键词不视为错误，也不触发平台检查：

```python
keyword = (keyword or "").strip()
if not keyword:
    self._last_error = ""
    return []
```

说明：

```text
UI 层负责提示“请输入关键词”。
Core 层只返回空列表。
```

---

### 16.2 平台不支持

如果 `_ensure_supported()` 返回错误：

```python
error = self._ensure_supported()
if error:
    self._last_error = error
    logger.warning(error)
    return []
```

可能返回：

```text
当前窗口连接功能仅支持 Windows 10 / Windows 11
```

或：

```text
缺少窗口连接依赖，请安装 pywin32 和 psutil
```

---

### 16.3 单个窗口异常

单个窗口处理异常时：

```text
跳过该窗口，继续枚举其他窗口。
```

不应：

- 抛出异常到 UI；
- 中断整个搜索；
- 修改 `_last_error` 为单窗口错误。

---

### 16.4 整体搜索异常

如果 `EnumWindows` 或搜索主流程发生整体异常：

```text
捕获异常，记录日志，写入 _last_error，返回当前已收集结果。
```

推荐：

```python
except Exception as exc:
    self._last_error = str(exc)
    logger.exception("搜索窗口时发生未知异常")
    return results
```

---

## 17. 与 P0-02 的关系

P0-02 阶段 `search_windows()` 当前行为为：

```python
logger.info("开始搜索窗口，关键词：%s", keyword)

# P0-03 阶段实现真实搜索逻辑
logger.info("搜索窗口完成，结果数量：0")
return []
```

P0-03 需要替换上述占位逻辑为真实 Windows API 枚举逻辑。

P0-03 不需要修改：

- `models.py`；
- `connect_window()` 的真实连接逻辑；
- `disconnect_window()`；
- `check_health()`；
- GUI 层。

但 P0-03 需要在 `window_manager.py` 中额外导入：

```python
WindowRect
```

用于搜索阶段的矩形计算。

---

## 18. 与后续 P0-04/P0-07 的关系

P0-03 产生的 `WindowInfo` 是后续连接流程的输入。

后续流程：

```text
P0-03 search_windows()
    ↓
WindowInfo
    ↓
P0-04 connect_window() 重新校验
    ↓
P0-05 获取窗口矩形与客户区矩形
    ↓
P0-06 激活窗口
    ↓
P0-07 保存 ConnectedWindow
```

注意：

```text
P0-03 不保证 WindowInfo 在连接时仍然有效。
```

因此 P0-04 必须重新校验。

还需要特别注意：

```text
P0-03 可能返回 is_minimized=True 的 WindowInfo。
P0-04 连接时必须重新检查当前窗口是否最小化。
如果当前仍最小化，连接失败。
如果用户已恢复窗口，则可以继续连接流程。
```

---

## 19. 数据对象构造规则

### 19.1 WindowInfo 构造

搜索命中窗口时，构造：

```python
WindowInfo(
    hwnd=hwnd,
    title=title,
    process_name=process_name,
    pid=pid,
    width=rect.width,
    height=rect.height,
    match_score=match_score,
    is_visible=is_visible,
    is_minimized=is_minimized,
)
```

---

### 19.2 字段来源

| 字段 | 来源 |
|---|---|
| `hwnd` | `EnumWindows` 回调参数 |
| `title` | `win32gui.GetWindowText(hwnd).strip()` |
| `process_name` | `psutil.Process(pid).name()` |
| `pid` | `win32process.GetWindowThreadProcessId(hwnd)` |
| `width` | 搜索用 `WindowRect.width` |
| `height` | 搜索用 `WindowRect.height` |
| `match_score` | `_calculate_match_score()` |
| `is_visible` | `win32gui.IsWindowVisible(hwnd)` |
| `is_minimized` | `win32gui.IsIconic(hwnd)` |

---

## 20. 最终代码设计

以下为 P0-03 完成后的 `window_manager.py` 推荐实现。

> 说明：该代码基于 P0-02 已完成代码进行增量扩展，重点替换 `search_windows()` 并新增搜索相关私有方法。

```python
from __future__ import annotations

import logging
import platform
from typing import Optional

from nzfz_executor.core.models import (
    WindowRect,
    WindowInfo,
    ConnectedWindow,
    ConnectOptions,
    ConnectResult,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import psutil
        import win32gui
        import win32process
    except ImportError:
        psutil = None
        win32gui = None
        win32process = None
else:
    psutil = None
    win32gui = None
    win32process = None


class WindowManager:
    """
    Windows 游戏窗口连接管理器。

    职责：
    - 搜索真实 Windows 顶层窗口
    - 连接并绑定指定窗口
    - 保存当前连接窗口上下文
    - 断开连接
    - 健康检测

    不负责：
    - GUI 状态切换
    - QThread/QTimer
    - 自动点击
    - 截图识别
    - 后台命令
    - 自动重连
    - 多窗口会话管理
    """

    MIN_WINDOW_WIDTH = 200
    MIN_WINDOW_HEIGHT = 150

    def __init__(self):
        self._connected_window: Optional[ConnectedWindow] = None
        self._last_window_info: Optional[WindowInfo] = None
        self._last_error: str = ""

    def search_windows(self, keyword: str) -> list[WindowInfo]:
        """
        搜索匹配关键词的可见窗口。

        匹配范围：
        - 窗口标题
        - 进程名称
        - PID

        Args:
            keyword: 用户输入的搜索关键词。

        Returns:
            匹配的 WindowInfo 列表，按 match_score 降序排列。
        """
        keyword = (keyword or "").strip()
        if not keyword:
            self._last_error = ""
            return []

        error = self._ensure_supported()
        if error:
            self._last_error = error
            logger.warning(error)
            return []

        logger.info("开始搜索窗口，关键词：%s", keyword)

        results: list[WindowInfo] = []

        def enum_callback(hwnd: int, extra) -> bool:
            window_info = self._build_window_info_if_match(
                hwnd=hwnd,
                keyword=keyword,
            )
            if window_info is not None:
                results.append(window_info)

            # 返回 True 表示继续枚举
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("搜索窗口时发生未知异常")
            return results

        results.sort(key=lambda item: item.match_score, reverse=True)

        self._last_error = ""
        logger.info("搜索窗口完成，结果数量：%s", len(results))

        return results

    def connect_window(
        self,
        window: WindowInfo,
        options: Optional[ConnectOptions] = None,
    ) -> ConnectResult:
        """
        连接指定窗口。

        Args:
            window: 搜索结果中的窗口信息。
            options: 连接选项。

        Returns:
            ConnectResult

        P0-04 ~ P0-07 阶段实现真实连接逻辑。
        """
        error = self._ensure_supported()
        if error:
            self._last_error = error
            logger.warning(error)
            return ConnectResult.fail(error)

        if window is None:
            message = "未选择窗口"
            self._last_error = message
            logger.warning(message)
            return ConnectResult.fail(message)

        options = options or ConnectOptions()

        logger.info(
            "开始连接窗口：title=%s, process=%s, pid=%s, hwnd=%s, control_mode=%s",
            window.title,
            window.process_name,
            window.pid,
            window.hwnd,
            options.control_mode.value,
        )

        # P0-04 ~ P0-07 阶段实现真实连接逻辑
        message = "窗口连接功能尚未实现"
        self._last_error = message
        logger.warning(message)
        return ConnectResult.fail(message)

    def disconnect_window(self) -> None:
        """
        断开当前连接，清理内部状态。

        注意：
        - 不关闭游戏窗口
        - 不最小化游戏窗口
        - 不改变游戏前台状态
        - 不发送任何输入
        """
        if self._connected_window is not None:
            logger.info(
                "断开窗口连接：title=%s, pid=%s, hwnd=%s",
                self._connected_window.title,
                self._connected_window.pid,
                self._connected_window.hwnd,
            )
        else:
            logger.info("断开窗口连接：当前未连接")

        self._connected_window = None
        self._last_error = ""

    def check_health(self) -> HealthCheckResult:
        """
        检查当前连接窗口是否正常。

        P0-02 阶段：
        - 未连接返回 NOT_CONNECTED
        - 已连接暂时返回 HEALTHY

        真实健康检测逻辑在 P1-01 阶段实现。
        """
        if self._connected_window is None:
            return HealthCheckResult(
                status=HealthStatus.NOT_CONNECTED,
                message="未连接",
                window=None,
            )

        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="连接正常",
            window=self._connected_window,
        )

    def get_connected_window(self) -> Optional[ConnectedWindow]:
        """
        获取当前已连接窗口。

        Returns:
            未连接时返回 None。
        """
        return self._connected_window

    def get_last_error(self) -> str:
        """
        获取最近一次错误信息。
        """
        return self._last_error

    def get_last_window_info(self) -> Optional[WindowInfo]:
        """
        获取最近一次连接使用的搜索结果。
        """
        return self._last_window_info

    def is_supported(self) -> bool:
        """
        当前运行环境是否支持窗口连接能力。
        """
        return self._ensure_supported() is None

    def get_unsupported_reason(self) -> str:
        """
        获取当前运行环境不支持窗口连接能力的原因。
        """
        return self._ensure_supported() or ""

    def _ensure_supported(self) -> Optional[str]:
        """
        检查当前环境是否支持窗口连接能力。

        Returns:
            None 表示支持。
            str 表示不支持原因。
        """
        if not IS_WINDOWS:
            return "当前窗口连接功能仅支持 Windows 10 / Windows 11"

        if win32gui is None or win32process is None or psutil is None:
            return "缺少窗口连接依赖，请安装 pywin32 和 psutil"

        return None

    def _build_window_info_if_match(
        self,
        hwnd: int,
        keyword: str,
    ) -> Optional[WindowInfo]:
        """
        根据 hwnd 构造匹配的 WindowInfo。

        如果窗口无效、不符合基础过滤条件或不匹配关键词，则返回 None。
        """
        try:
            if not win32gui.IsWindow(hwnd):
                return None

            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            if not is_visible:
                return None

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return None

            is_minimized = bool(win32gui.IsIconic(hwnd))

            rect = self._get_search_window_rect(
                hwnd=hwnd,
                is_minimized=is_minimized,
            )
            if rect is None:
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None

            process_name = self._get_process_name(pid)
            if not process_name:
                return None

            match_score = self._calculate_match_score(
                keyword=keyword,
                title=title,
                process_name=process_name,
                pid=pid,
            )

            if match_score <= 0:
                return None

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                pid=pid,
                width=rect.width,
                height=rect.height,
                match_score=match_score,
                is_visible=is_visible,
                is_minimized=is_minimized,
            )

        except Exception as exc:
            logger.debug(
                "构造窗口搜索结果失败，hwnd=%s，错误：%s",
                hwnd,
                exc,
            )
            return None

    def _get_search_window_rect(
        self,
        hwnd: int,
        is_minimized: bool,
    ) -> Optional[WindowRect]:
        """
        获取搜索阶段使用的窗口矩形。

        非最小化窗口：
        - 使用 GetWindowRect(hwnd)

        最小化窗口：
        - 使用 GetWindowPlacement(hwnd) 中的 rcNormalPosition
        """
        try:
            if is_minimized:
                placement = win32gui.GetWindowPlacement(hwnd)
                rc_normal = placement[4]
                left, top, right, bottom = rc_normal
            else:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)

            rect = WindowRect(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )

            if not rect.is_valid(
                min_width=self.MIN_WINDOW_WIDTH,
                min_height=self.MIN_WINDOW_HEIGHT,
            ):
                return None

            return rect

        except Exception as exc:
            logger.debug(
                "获取搜索窗口矩形失败，hwnd=%s, is_minimized=%s, 错误：%s",
                hwnd,
                is_minimized,
                exc,
            )
            return None

    @staticmethod
    def _calculate_match_score(
        keyword: str,
        title: str,
        process_name: str,
        pid: int,
    ) -> float:
        """
        计算窗口搜索匹配分数。

        匹配范围：
        - PID 精确匹配
        - 标题完全匹配
        - 进程名完全匹配
        - 标题包含匹配
        - 进程名包含匹配
        """
        keyword = (keyword or "").lower().strip()
        title_lower = (title or "").lower()
        process_lower = (process_name or "").lower()

        if not keyword:
            return 0.0

        if keyword.isdigit():
            try:
                if int(keyword) == pid:
                    return 1.0
            except ValueError:
                pass

        if title_lower == keyword:
            return 1.0

        if process_lower == keyword:
            return 0.95

        if keyword in title_lower:
            return 0.85

        if keyword in process_lower:
            return 0.8

        return 0.0

    def _get_process_name(self, pid: int) -> Optional[str]:
        """
        根据 PID 获取进程名。

        搜索阶段获取失败时返回 None，不向外抛异常。
        """
        try:
            process = psutil.Process(pid)
            name = process.name()
            return name.strip() if name else None
        except Exception as exc:
            logger.debug(
                "获取进程名失败，pid=%s，错误：%s",
                pid,
                exc,
            )
            return None
```

---

## 21. 单元测试建议

P0-03 涉及真实 Windows API，测试可分为两类：

```text
纯逻辑测试
Windows 环境集成测试
```

---

### 21.1 纯逻辑测试：匹配分数

测试 `_calculate_match_score()`。

```python
from nzfz_executor.core.window_manager import WindowManager


def test_calculate_match_score_by_pid():
    score = WindowManager._calculate_match_score(
        keyword="1234",
        title="逆战",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 1.0


def test_calculate_match_score_title_exact():
    score = WindowManager._calculate_match_score(
        keyword="逆战",
        title="逆战",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 1.0


def test_calculate_match_score_process_exact():
    score = WindowManager._calculate_match_score(
        keyword="nz.exe",
        title="逆战",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 0.95


def test_calculate_match_score_title_contains():
    score = WindowManager._calculate_match_score(
        keyword="逆战",
        title="逆战：未来",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 0.85


def test_calculate_match_score_process_contains():
    score = WindowManager._calculate_match_score(
        keyword="nz",
        title="Game",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 0.8


def test_calculate_match_score_no_match():
    score = WindowManager._calculate_match_score(
        keyword="not-exists",
        title="逆战",
        process_name="nz.exe",
        pid=1234,
    )

    assert score == 0.0
```

---

### 21.2 空关键词测试

空关键词不触发平台检查，无论是否 Windows 都应返回空列表。

```python
from nzfz_executor.core.window_manager import WindowManager


def test_search_windows_empty_keyword():
    manager = WindowManager()

    results = manager.search_windows("")

    assert results == []
    assert manager.get_last_error() == ""


def test_search_windows_none_keyword():
    manager = WindowManager()

    results = manager.search_windows(None)

    assert results == []
    assert manager.get_last_error() == ""
```

---

### 21.3 非 Windows 平台测试

在非 Windows 平台：

```python
def test_search_windows_not_supported():
    manager = WindowManager()

    if not manager.is_supported():
        results = manager.search_windows("逆战")
        assert results == []
        assert manager.get_last_error() != ""
```

---

### 21.4 Windows 集成测试：按标题搜索

在 Windows 上打开一个已知标题窗口，例如记事本。

```python
def test_search_windows_by_title_on_windows():
    manager = WindowManager()

    if not manager.is_supported():
        return

    results = manager.search_windows("记事本")

    assert isinstance(results, list)
    assert all(item.match_score > 0 for item in results)
```

---

### 21.5 Windows 集成测试：按进程名搜索

```python
def test_search_windows_by_process_name_on_windows():
    manager = WindowManager()

    if not manager.is_supported():
        return

    results = manager.search_windows("notepad.exe")

    assert isinstance(results, list)

    if results:
        assert any("notepad" in item.process_name.lower() for item in results)
```

---

### 21.6 Windows 集成测试：按 PID 搜索

可先通过搜索进程名拿到一个 PID，再用 PID 反查。

```python
def test_search_windows_by_pid_on_windows():
    manager = WindowManager()

    if not manager.is_supported():
        return

    first_results = manager.search_windows("notepad.exe")
    if not first_results:
        return

    pid = first_results[0].pid
    results = manager.search_windows(str(pid))

    assert any(item.pid == pid for item in results)
```

---

### 21.7 Windows 集成测试：最小化窗口搜索

测试步骤：

```text
1. 打开记事本；
2. 最小化记事本窗口；
3. 搜索 notepad.exe；
4. 确认结果中可包含 is_minimized=True 的窗口；
5. 确认 width / height 来自恢复矩形，并满足最低尺寸要求。
```

示例：

```python
def test_search_minimized_window_on_windows():
    manager = WindowManager()

    if not manager.is_supported():
        return

    results = manager.search_windows("notepad.exe")

    assert isinstance(results, list)

    minimized_results = [
        item for item in results
        if item.is_minimized
    ]

    for item in minimized_results:
        assert item.width >= manager.MIN_WINDOW_WIDTH
        assert item.height >= manager.MIN_WINDOW_HEIGHT
```

---

## 22. 验收标准

### 22.1 基础验收

- [ ] `WindowManager.search_windows()` 不再固定返回空列表；
- [ ] Windows 支持环境下可以枚举真实窗口；
- [ ] 非 Windows 平台不会崩溃；
- [ ] 缺少 `pywin32` 或 `psutil` 时不会崩溃；
- [ ] 空关键词返回空列表；
- [ ] 空关键词不触发平台检查；
- [ ] 空关键词会清空 `_last_error`；
- [ ] 单个窗口处理异常不会导致整个搜索失败；
- [ ] `search_windows()` 不更新 `_last_window_info`；
- [ ] `search_windows()` 不更新 `_connected_window`。

---

### 22.2 搜索能力验收

- [ ] 输入已存在窗口标题，可搜索到目标窗口；
- [ ] 输入进程名，可搜索到目标窗口；
- [ ] 输入 PID，可搜索到目标窗口；
- [ ] 标题匹配忽略大小写；
- [ ] 进程名匹配忽略大小写；
- [ ] PID 匹配为数字关键词精确匹配；
- [ ] 不匹配窗口不会出现在结果中；
- [ ] 最小化窗口如果标题/进程名/PID 匹配，可以出现在搜索结果中；
- [ ] 最小化窗口搜索结果中 `is_minimized=True`；
- [ ] 最小化窗口尺寸来自恢复矩形；
- [ ] 恢复矩形无效的最小化窗口不会出现在搜索结果中。

---

### 22.3 搜索结果字段验收

搜索结果中的每个 `WindowInfo` 必须满足：

- [ ] 包含 `hwnd`；
- [ ] 包含 `title`；
- [ ] 包含 `process_name`；
- [ ] 包含 `pid`；
- [ ] 包含 `width`；
- [ ] 包含 `height`；
- [ ] 包含 `match_score`；
- [ ] 包含 `is_visible`；
- [ ] 包含 `is_minimized`；
- [ ] `width >= 200`；
- [ ] `height >= 150`；
- [ ] `match_score > 0`。

---

### 22.4 排序验收

- [ ] 搜索结果按 `match_score` 降序排列；
- [ ] 相同分数保持枚举顺序；
- [ ] PID 精确匹配分数为 `1.0`；
- [ ] 标题完全匹配分数为 `1.0`；
- [ ] 进程名完全匹配分数为 `0.95`；
- [ ] 标题包含匹配分数为 `0.85`；
- [ ] 进程名包含匹配分数为 `0.8`。

---

### 22.5 最小化窗口连接边界验收

P0-03 只负责搜索，但需要保证与 P0-04 的边界明确：

- [ ] P0-03 可以返回 `is_minimized=True` 的搜索结果；
- [ ] P0-03 不自动恢复最小化窗口；
- [ ] P0-03 不连接最小化窗口；
- [ ] P0-04 连接时仍必须重新检查 `IsIconic(hwnd)`；
- [ ] 如果连接时窗口仍最小化，应提示 `窗口已最小化，请恢复窗口后重试`；
- [ ] 如果搜索时最小化，但连接前用户已恢复窗口，则 P0-04 可以继续后续连接校验。

---

### 22.6 日志验收

- [ ] 搜索开始有日志；
- [ ] 搜索完成有结果数量日志；
- [ ] 单窗口异常不会中断搜索；
- [ ] 整体搜索异常有错误日志；
- [ ] 平台不支持有 warning 日志；
- [ ] 依赖缺失有 warning 日志。

---

## 23. GUI 接入注意事项

P0-03 是 Core 层能力，GUI 层后续 P1-02 接入时应遵守以下规则。

### 23.1 GUI 不直接调用 Windows API

错误做法：

```python
win32gui.EnumWindows(...)
win32gui.GetWindowText(hwnd)
```

正确做法：

```python
windows = self.window_manager.search_windows(keyword)
```

---

### 23.2 搜索结果显示字段

UI 表格默认显示三列：

```text
窗口标题 | 进程名 | PID
```

不直接显示：

```text
hwnd
match_score
is_visible
is_minimized
```

---

### 23.3 保存完整 WindowInfo

GUI 表格第一列必须通过 `Qt.UserRole` 保存完整 `WindowInfo`：

```python
item = QTableWidgetItem(window.title)
item.setData(Qt.UserRole, window)
self.result_table.setItem(row, 0, item)
```

不应从表格文本反推窗口对象。

---

### 23.4 最小化窗口提示

如果搜索结果中存在：

```python
window.is_minimized is True
```

GUI 层可以选择：

```text
1. 保持三列表格不变；
2. 在选中该行时显示提示；
3. 或在连接失败时展示错误。
```

推荐提示文案：

```text
该窗口当前已最小化，连接前请先恢复窗口。
```

当前版本不强制新增表格列。

---

## 24. 风险与处理策略

### 24.1 权限不足导致获取进程名失败

风险：

```text
某些高权限进程可能导致 psutil 获取进程名失败。
```

处理：

```text
搜索阶段跳过该窗口，不中断整体搜索。
```

用户排查建议：

```text
如果目标游戏窗口搜索不到，请尝试以管理员身份运行工具。
```

---

### 24.2 系统窗口过多

风险：

```text
EnumWindows 会枚举大量窗口。
```

处理：

```text
基础过滤尽早执行，减少后续 psutil 调用。
```

过滤顺序建议：

```text
IsWindow
IsWindowVisible
GetWindowText
IsIconic
获取搜索用窗口矩形
GetWindowThreadProcessId
psutil.Process(pid).name()
match_score
```

---

### 24.3 搜索结果是快照

风险：

```text
用户点击连接时，窗口可能已经关闭、隐藏、最小化、恢复或 PID 变化。
```

处理：

```text
P0-04 必须重新校验，不信任搜索结果。
```

---

### 24.4 最小化窗口矩形不稳定

风险：

```text
最小化窗口直接调用 GetWindowRect 可能返回异常坐标或非预期尺寸。
```

处理：

```text
P0-03 对最小化窗口使用 GetWindowPlacement().rcNormalPosition 计算恢复后尺寸。
```

---

### 24.5 搜索到但无法连接

风险：

```text
搜索结果中包含最小化窗口，用户点击连接时仍然失败。
```

处理：

```text
这是当前版本设计行为。
搜索支持最小化窗口；
连接不支持当前仍处于最小化状态的窗口。
UI 应提示用户恢复窗口后重试。
```

---

### 24.6 非 Windows 平台

风险：

```text
macOS/Linux 环境没有 pywin32。
```

处理：

```text
P0-02 已实现安全导入和 _ensure_supported()。
P0-03 必须继续复用该机制。
```

---

## 25. 最终交付清单

P0-03 完成后，至少应在：

```text
nzfz_executor/core/window_manager.py
```

中完成：

- [ ] `search_windows()` 真实实现；
- [ ] `MIN_WINDOW_WIDTH`；
- [ ] `MIN_WINDOW_HEIGHT`；
- [ ] `_build_window_info_if_match()`；
- [ ] `_get_search_window_rect()`；
- [ ] `_calculate_match_score()`；
- [ ] `_get_process_name()`；
- [ ] 非最小化窗口使用 `GetWindowRect()`；
- [ ] 最小化窗口使用 `GetWindowPlacement().rcNormalPosition`；
- [ ] 搜索开始日志；
- [ ] 搜索完成日志；
- [ ] 单窗口异常保护；
- [ ] 平台不支持处理；
- [ ] 依赖缺失处理；
- [ ] 空关键词先处理；
- [ ] 搜索结果按 `match_score` 降序排序；
- [ ] `search_windows()` 不更新 `_last_window_info`；
- [ ] `search_windows()` 不更新 `_connected_window`。

不需要修改：

```text
nzfz_executor/core/models.py
```

除非前置模型尚未按 P0-01 完成。

---

## 26. 最终结论

P0-03 的核心是将 P0-02 中的 `search_windows()` 从占位实现升级为真实 Windows API 搜索能力。

本阶段完成后，执行器 Core 层将具备以下能力：

1. 能在 Windows 10 / Windows 11 上枚举真实顶层窗口；
2. 能按窗口标题搜索；
3. 能按进程名搜索；
4. 能按 PID 搜索；
5. 能返回包含 `hwnd` 的 `WindowInfo`；
6. 能过滤无效、小尺寸、不可见、无标题、无进程名窗口；
7. 能支持搜索最小化窗口；
8. 能通过 `is_minimized` 标记最小化窗口；
9. 能使用恢复矩形计算最小化窗口搜索尺寸；
10. 能按匹配分数排序搜索结果；
11. 能安全处理单窗口异常；
12. 能在非 Windows 或依赖缺失时安全返回；
13. 能为空关键词提供稳定行为；
14. 为后续 P0-04 真实连接校验提供可靠输入。

当前版本明确边界：

```text
P0-03 支持搜索最小化窗口；
P0-04 仍禁止连接当前最小化窗口；
当前版本不自动恢复最小化窗口。
```

P0-03 完成后，下一步应进入：

```text
P0-04 连接前窗口有效性校验
```

即在用户选择 `WindowInfo` 并点击连接时，重新校验目标窗口当前状态。