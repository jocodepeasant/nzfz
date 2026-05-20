# Tasks

- [x] Task 1: 修复 overlay.show() 顺序 + GUI 不缩小
  - [x] SubTask 1.1: 修改 `app.py` 的 `connect_window_by_hwnd`，先调用 `self.focus_force()` 再调用 `self._overlay.show()`
  - [x] SubTask 1.2: 修改 `overlay.py` 的 `show()`，先 `SetWindowPos(..., SWP_NOACTIVATE)` 再 `ShowWindow(..., SW_SHOWNOACTIVATE)`
  - [x] SubTask 1.3: 在 `show()` 成功后记录 `_last_rect` 供同步使用

- [x] Task 2: 修复 send_click 坐标转换逻辑
  - [x] SubTask 2.1: 修改 `input.py` 的 `send_click`，新增 `game_hwnd` 参数，使用 `ClientToScreen → ScreenToClient` 双重转换
  - [x] SubTask 2.2: 修改 `action.py` 的 `click_at`，传入 `game_hwnd=rect.hwnd`
  - [x] SubTask 2.3: 修改 `action.py` 的 `ensure_map_open`，传入 game_hwnd
  - [x] SubTask 2.4: 修改 `slot.py` 的 `click_slot`，传入 game_hwnd

- [x] Task 3: 实现 overlay 位置同步
  - [x] SubTask 3.1: 在 `overlay.py` 的 `WindowOverlay` 新增 `_sync_position()` 方法，用 `GetWindowRect` 检查窗口位置变化
  - [x] SubTask 3.2: 新增 `_start_sync_timer()` 启动每 500ms 定时同步
  - [x] SubTask 3.3: 在 `hide()` 中停止定时器
  - [x] SubTask 3.4: 窗口无效时自动调用 `hide()`

- [x] Task 4: 添加开发模式窗口信息显示
  - [x] SubTask 4.1: 修改 `overlay.py` 的 `_redraw`，增加窗口信息文本（标题+hwnd）和操作日志
  - [x] SubTask 4.2: 新增 `_debug_info` 属性（窗口标题+hwnd）和 `_log_lines` 属性
  - [x] SubTask 4.3: `show(hwnd, window_info)` 接收窗口信息参数
  - [x] SubTask 4.4: `log_operation(msg)` 方法添加日志行
  - [x] SubTask 4.5: `app.py` 调用 `connect_window_by_hwnd` 时传入窗口信息

- [x] Task 5: 同步测试
  - [x] SubTask 5.1: 更新 `test_input.py` 中 send_click 测试以反映新签名
  - [x] SubTask 5.2: 添加 overlay 位置同步测试
  - [x] SubTask 5.3: 添加开发模式显示测试
  - [x] SubTask 5.4: 运行全部测试确保通过

# Task Dependencies

- Task 1 无依赖
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1
- Task 4 依赖 Task 1
- Task 5 依赖 Task 1~4
