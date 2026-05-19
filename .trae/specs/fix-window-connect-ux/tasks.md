# Tasks

- [x] Task 1: 新增 list_windows 函数
  - [x] SubTask 1.1: 在 `runtime/window.py` 中实现 `list_windows(title_keyword="")` 函数，Windows 平台使用 ctypes EnumWindows 枚举可见窗口，返回 `list[dict]`（每项含 hwnd 和 title）
  - [x] SubTask 1.2: 非 Windows 平台返回空列表
  - [x] SubTask 1.3: 编写 list_windows 单元测试

- [x] Task 2: 修复 GUI 窗口缩小问题
  - [x] SubTask 2.1: 修改 `app.py` 的 `connect_window` 方法，连接成功后调用 `focus_force()` 保持 GUI 焦点

- [x] Task 3: 实现窗口选择对话框
  - [x] SubTask 3.1: 创建 `ui/window_select_dialog.py`，实现 `WindowSelectDialog(tk.Toplevel)` 类
  - [x] SubTask 3.2: 对话框包含 Treeview（序号、窗口标题、句柄）、连接按钮、取消按钮
  - [x] SubTask 3.3: 对话框为模态窗口，居中显示在主窗口上，大小约 500x400
  - [x] SubTask 3.4: 未选中行时"连接"按钮禁用

- [x] Task 4: 实现断开连接功能
  - [x] SubTask 4.1: 修改 `script_tab.py`，连接成功后按钮文本变为"断开连接"，点击调用 `app.disconnect_window()`
  - [x] SubTask 4.2: 断开连接时清除状态栏、画面标签页截图，按钮恢复为"连接窗口"
  - [x] SubTask 4.3: 执行器运行中时"断开连接"按钮禁用

- [x] Task 5: 修改连接窗口按钮交互流程
  - [x] SubTask 5.1: 修改 `script_tab.py` 的 `_on_connect_window`，点击后调用 `list_windows` 获取窗口列表
  - [x] SubTask 5.2: 无匹配窗口时弹出提示，有匹配时弹出 `WindowSelectDialog`
  - [x] SubTask 5.3: 用户选择窗口后调用 `app.connect_window_by_hwnd(hwnd)` 完成连接
  - [x] SubTask 5.4: 在 `app.py` 新增 `connect_window_by_hwnd(hwnd)` 方法，根据 hwnd 获取 rect 并设置连接

- [x] Task 6: 编写测试
  - [x] SubTask 6.1: 测试 list_windows 函数
  - [x] SubTask 6.2: 测试 connect_window_by_hwnd 方法
  - [x] SubTask 6.3: 测试断开连接逻辑（通过 script_tab 按钮状态测试覆盖）

# Task Dependencies

- Task 1 无依赖（独立模块）
- Task 2 无依赖（独立修复）
- Task 3 依赖 Task 1（需要 list_windows 获取窗口列表）
- Task 4 无依赖（独立功能）
- Task 5 依赖 Task 1、Task 3、Task 4（需要窗口列表、选择对话框、断开连接）
- Task 6 依赖 Task 1~5
