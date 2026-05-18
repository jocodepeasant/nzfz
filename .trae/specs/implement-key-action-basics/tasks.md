# Tasks

- [x] Task 1: 实现输入库导入与降级机制
  - [x] SubTask 1.1: 在 action.py 顶部添加 `try/except ImportError` 检测 pynput 和 pyautogui 可用性
  - [x] SubTask 1.2: 设置模块级标志 `_PYNPUT_AVAILABLE` 和 `_PYAUTOGUI_AVAILABLE`
  - [x] SubTask 1.3: 定义特殊键映射字典 `_SPECIAL_KEY_MAP`（enter, space, esc, tab 等）

- [x] Task 2: 实现 press_key 按键模拟函数
  - [x] SubTask 2.1: 实现短按逻辑（press + release）
  - [x] SubTask 2.2: 实现长按逻辑（press → time.sleep → release），hold_ms > 0 时生效
  - [x] SubTask 2.3: 实现特殊键映射，将 "enter" 等字符串映射为 pynput.keyboard.Key 枚举
  - [x] SubTask 2.4: pynput 不可用时打印 warning 并抛出 RuntimeError

- [x] Task 3: 实现 click_at 鼠标点击函数
  - [x] SubTask 3.1: 使用 pyautogui.click(x, y, button=button) 实现点击
  - [x] SubTask 3.2: 支持 button="left" 和 button="right"
  - [x] SubTask 3.3: pyautogui 不可用时打印 warning 并抛出 RuntimeError

- [x] Task 4: 实现 drag 拖拽函数
  - [x] SubTask 4.1: 使用 pyautogui 实现 moveTo → mouseDown → moveTo → mouseUp 拖拽流程
  - [x] SubTask 4.2: duration_ms 转换为秒传给 pyautogui 的 duration 参数
  - [x] SubTask 4.3: pyautogui 不可用时打印 warning 并抛出 RuntimeError

- [x] Task 5: 实现 ensure_map_open 地图界面检测与打开函数
  - [x] SubTask 5.1: 创建 VisionDetector 实例，调用 is_map_ui_open 检测地图界面
  - [x] SubTask 5.2: 未打开时调用 press_key("o")，等待 MAP_OPEN_WAIT_MS 后再次检测
  - [x] SubTask 5.3: 实现重试逻辑，最多 MAP_OPEN_MAX_RETRIES 次
  - [x] SubTask 5.4: 全部失败返回 False，成功返回 True

- [x] Task 6: 实现 execute_action 动作调度入口
  - [x] SubTask 6.1: 根据 action["type"] 分发到对应处理逻辑
  - [x] SubTask 6.2: 实现 type="log" 处理：打印消息，返回成功结果
  - [x] SubTask 6.3: 其他已知类型返回 not implemented 错误
  - [x] SubTask 6.4: 未知类型打印 warning 并返回错误

- [x] Task 7: 更新 engine/__init__.py 导出
  - [x] SubTask 7.1: 在 __init__.py 中添加 press_key, click_at, drag, ensure_map_open, execute_action 的导入和导出

- [x] Task 8: 编写测试 test_action.py
  - [x] SubTask 8.1: 测试 press_key 短按/长按/特殊键/降级
  - [x] SubTask 8.2: 测试 click_at 左键/右键/降级
  - [x] SubTask 8.3: 测试 drag 默认时长/自定义时长/降级
  - [x] SubTask 8.4: 测试 ensure_map_open 已打开/未打开/重试失败
  - [x] SubTask 8.5: 测试 execute_action log/未实现类型/未知类型

# Task Dependencies

- Task 2 依赖 Task 1（需要输入库导入机制）
- Task 3 依赖 Task 1（需要输入库导入机制）
- Task 4 依赖 Task 1（需要输入库导入机制）
- Task 5 依赖 Task 2（ensure_map_open 调用 press_key）
- Task 6 无外部依赖，可与 Task 2~5 并行
- Task 7 依赖 Task 2~6（需要所有函数实现完成）
- Task 8 依赖 Task 2~7（需要所有函数实现完成）
