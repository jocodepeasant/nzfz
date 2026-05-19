# Tasks

- [x] Task 1: 新增 runtime/overlay.py 窗口覆盖层模块
  - [x] SubTask 1.1: 实现 `WindowOverlay` 类，使用 ctypes 创建透明分层窗口（WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST）
  - [x] SubTask 1.2: 实现 `show(hwnd)` 方法：创建覆盖层窗口，绘制红色边框，覆盖在目标窗口客户区上方
  - [x] SubTask 1.3: 实现 `hide()` 方法：销毁覆盖层窗口
  - [x] SubTask 1.4: 实现 `draw_click_marker(x, y, duration_ms=1500)` 方法：在指定位置绘制红色十字标记，定时自动清除
  - [x] SubTask 1.5: 实现 `draw_key_info(key, hold_ms=0, duration_ms=2000)` 方法：在左上角显示按键信息，定时自动清除
  - [x] SubTask 1.6: 非 Windows 平台 WindowOverlay 为空实现（show/hide/draw 方法均为 no-op）

- [x] Task 2: 执行前聚焦游戏窗口
  - [x] SubTask 2.1: 修改 `executor_bridge.py` 的 `_execute_script`，在执行前调用 `focus_window(rect.hwnd)`
  - [x] SubTask 2.2: 每个波次开始前检查 `is_window_valid(rect.hwnd)`，无效则停止执行

- [x] Task 3: 连接/断开时管理 overlay
  - [x] SubTask 3.1: 修改 `app.py`，新增 `_overlay` 属性（`WindowOverlay | None`）
  - [x] SubTask 3.2: `connect_window_by_hwnd` 成功后创建 overlay 并 show
  - [x] SubTask 3.3: `disconnect_window` 时销毁 overlay
  - [x] SubTask 3.4: `connect_window` 成功后也创建 overlay 并 show

- [x] Task 4: Debug 模式开关
  - [x] SubTask 4.1: 在 `script_tab.py` 运行参数区新增"调试模式"复选框
  - [x] SubTask 4.2: 将 debug 模式状态传入 `executor_bridge.start_execution`

- [x] Task 5: Debug 模式操作可视化
  - [x] SubTask 5.1: 修改 `action.py` 的 `click_at` 函数，新增可选 `overlay` 参数，调用 `overlay.draw_click_marker`
  - [x] SubTask 5.2: 修改 `action.py` 的 `press_key` 函数，新增可选 `overlay` 参数，调用 `overlay.draw_key_info`
  - [x] SubTask 5.3: 修改 `executor_bridge.py`，将 overlay 传入 context，ActionExecutor 执行时传递 overlay
  - [x] SubTask 5.4: 修改 `slot.py` 的 `click_slot`，将 overlay 传递给 `click_at`

- [x] Task 6: 编写测试
  - [x] SubTask 6.1: 测试 WindowOverlay 非 Windows 平台为 no-op
  - [x] SubTask 6.2: 测试 executor_bridge 执行前调用 focus_window
  - [x] SubTask 6.3: 测试窗口失效时停止执行

# Task Dependencies

- Task 1 无依赖（独立模块）
- Task 2 无依赖（独立修改）
- Task 3 依赖 Task 1（需要 WindowOverlay）
- Task 4 无依赖（独立修改）
- Task 5 依赖 Task 1、Task 4（需要 WindowOverlay 和 debug 模式开关）
- Task 6 依赖 Task 1~5
