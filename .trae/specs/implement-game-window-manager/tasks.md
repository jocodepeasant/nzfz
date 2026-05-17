# Tasks

- [x] Task 1: 实现 WindowRect 数据类和 GameState 窗口状态扩展
  - [x] 1.1: 在 `runtime/window.py` 中定义 `WindowRect` 数据类（hwnd, left, top, width, height）
  - [x] 1.2: 扩展 `state.py` 的 `GameState`，添加 window_handle、window_rect、is_focused 字段及 update 方法

- [x] Task 2: 实现 Windows 平台的窗口管理函数
  - [x] 2.1: 实现 `find_game_window(title_keyword)` — 使用 win32gui.EnumWindows 遍历窗口，按标题关键字匹配
  - [x] 2.2: 实现 `focus_window(hwnd)` — 使用 win32gui.ShowWindow + SetForegroundWindow 置顶激活，处理最小化恢复
  - [x] 2.3: 实现 `get_window_rect(hwnd)` — 使用 win32gui.GetClientRect 获取客户区矩形，转换为客户区绝对坐标
  - [x] 2.4: 实现 `is_window_valid(hwnd)` — 使用 win32gui.IsWindow + IsWindowVisible 校验

- [x] Task 3: 实现非 Windows 平台降级方案
  - [x] 3.1: 在 `runtime/window.py` 中添加平台检测逻辑（sys.platform）
  - [x] 3.2: Linux/macOS 降级：使用 mss 获取屏幕尺寸，find_game_window 返回全屏区域，打印 warning

- [x] Task 4: 更新 CLI run 命令
  - [x] 4.1: 在 `cli.py` 的 `run_cmd` 中，非 dry-run 时调用 find_game_window 做前置窗口检测
  - [x] 4.2: 窗口检测失败时打印错误并以 exit code 1 退出
  - [x] 4.3: 窗口检测成功时打印窗口信息（标题、位置、尺寸）

- [x] Task 5: 验证与测试
  - [x] 5.1: 使用示例脚本 `td-executor validate ../schemas/examples/space_station_normal_baseline_v1.json` 确认校验仍正常
  - [x] 5.2: 使用 `td-executor run ../schemas/examples/space_station_normal_baseline_v1.json` 确认窗口检测逻辑触发
  - [x] 5.3: 确认 `ratio_to_pixel()` 可与 `get_window_rect()` 返回值正确配合

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2] and [Task 3]
- [Task 5] depends on [Task 4]
