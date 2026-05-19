# Tasks

- [x] Task 1: 新增 runtime/input.py 后台输入模块
  - [x] SubTask 1.1: 实现 `send_click(hwnd, x, y, button="left")` 函数，Windows 平台使用 PostMessageW 发送 WM_LBUTTONDOWN/UP 或 WM_RBUTTONDOWN/UP
  - [x] SubTask 1.2: 实现 `send_key(hwnd, key, hold_ms=0)` 函数，Windows 平台使用 PostMessageW 发送 WM_KEYDOWN/UP，使用 VkKeyScanW 获取虚拟键码
  - [x] SubTask 1.3: 非 Windows 平台降级为 pyautogui/pynput 前台输入
  - [x] SubTask 1.4: 实现 `MAKELPARAM` 辅助函数和 `lparam_for_key` 辅助函数

- [x] Task 2: 修改 click_at 和 press_key 使用后台输入
  - [x] SubTask 2.1: 修改 `action.py` 的 `click_at` 函数，新增 `hwnd=0` 参数，hwnd 非 0 时调用 `send_click(hwnd, x - rect_left, y - rect_top)`，否则降级为 pyautogui
  - [x] SubTask 2.2: 修改 `action.py` 的 `press_key` 函数，新增 `hwnd=0` 参数，hwnd 非 0 时调用 `send_key(hwnd, key, hold_ms)`，否则降级为 pynput
  - [x] SubTask 2.3: 修改 `slot.py` 的 `click_slot`，传入 `hwnd=context.get("rect").hwnd if context else 0`
  - [x] SubTask 2.4: 修改 `action.py` 的 `_execute_place_trap` 等方法，从 context["rect"] 获取 hwnd 传入 click_at/press_key

- [x] Task 3: map_ui_indicator 可选检测
  - [x] SubTask 3.1: 修改 `detector.py` 的 `is_map_ui_open`，缺少 `map_ui_indicator` 时返回 True 并记录 info 日志
  - [x] SubTask 3.2: 修改 `detect_error_tip`，缺少 `place_error_tip` 时返回 False 并记录 info 日志

- [x] Task 4: 移除 focus_window 调用
  - [x] SubTask 4.1: 修改 `executor_bridge.py` 的 `_execute_script`，移除 `focus_window(rect.hwnd)` 调用（保留 `is_window_valid` 检查）
  - [x] SubTask 4.2: 修改 `app.py` 的 `connect_window` 和 `connect_window_by_hwnd`，确保不调用 focus_window，连接完成后调用 `self.focus_force()`

- [x] Task 5: 编写测试
  - [x] SubTask 5.1: 测试 `send_click` 和 `send_key` 非 Windows 平台降级行为
  - [x] SubTask 5.2: 测试 `is_map_ui_open` 缺少 map_ui_indicator 时返回 True
  - [x] SubTask 5.3: 测试 `executor_bridge` 不再调用 focus_window

# Task Dependencies

- Task 1 无依赖（独立模块）
- Task 2 依赖 Task 1（需要 send_click/send_key）
- Task 3 无依赖（独立修改）
- Task 4 无依赖（独立修改）
- Task 5 依赖 Task 1~4
