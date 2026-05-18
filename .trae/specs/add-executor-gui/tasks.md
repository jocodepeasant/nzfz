# Tasks

- [x] Task 1: 创建 UI 包结构和事件系统
  - [x] SubTask 1.1: 创建 `td_executor/ui/__init__.py` 包
  - [x] SubTask 1.2: 创建 `td_executor/ui/events.py`，定义事件类型（ActionStartEvent, ActionCompleteEvent, WaveChangeEvent, ExecutionDoneEvent）
  - [x] SubTask 1.3: 创建 `td_executor/ui/executor_bridge.py`，实现执行器与 GUI 的线程安全桥接（Queue 通信、停止标志、子线程执行）

- [x] Task 2: 实现 GUI 主窗口
  - [x] SubTask 2.1: 创建 `td_executor/ui/app.py`，实现 ExecutorApp 类（tkinter.Tk 子类）
  - [x] SubTask 2.2: 实现 ttk.Notebook 四标签页布局
  - [x] SubTask 2.3: 实现底部状态栏（状态、窗口信息、时间）
  - [x] SubTask 2.4: 实现窗口关闭确认（运行中时弹出对话框）
  - [x] SubTask 2.5: 实现 launch() 函数入口，处理无显示环境异常

- [x] Task 3: 实现执行监控面板
  - [x] SubTask 3.1: 创建 `td_executor/ui/monitor_tab.py`，实现 MonitorTab 类
  - [x] SubTask 3.2: 实现 ttk.Treeview 动作列表（序号、类型、名称、状态、重试次数、耗时）
  - [x] SubTask 3.3: 实现状态颜色标识（待执行灰色、执行中蓝色、成功绿色、失败红色、跳过黄色）
  - [x] SubTask 3.4: 实现波次进度条和整体进度显示
  - [x] SubTask 3.5: 实现统计摘要面板（总动作数、成功数、失败数、跳过数、运行时长）
  - [x] SubTask 3.6: 实现 poll_queue 轮询更新机制

- [x] Task 4: 实现脚本管理与启动
  - [x] SubTask 4.1: 创建 `td_executor/ui/script_tab.py`，实现 ScriptTab 类
  - [x] SubTask 4.2: 实现脚本文件选择和路径输入
  - [x] SubTask 4.3: 实现脚本校验功能（调用 validate_script_data）
  - [x] SubTask 4.4: 实现脚本预览摘要显示
  - [x] SubTask 4.5: 实现运行参数配置（窗口标题、dry-run）
  - [x] SubTask 4.6: 实现启动/停止/重置控制按钮
  - [x] SubTask 4.7: 实现子线程执行逻辑（通过 executor_bridge）

- [x] Task 5: 实现运行报告查看
  - [x] SubTask 5.1: 创建 `td_executor/ui/report_tab.py`，实现 ReportTab 类
  - [x] SubTask 5.2: 实现历史报告列表（从 reports/ 目录加载）
  - [x] SubTask 5.3: 实现报告详情显示（动作日志表格 + 统计摘要）
  - [x] SubTask 5.4: 实现报告导出功能（保存为 JSON）
  - [x] SubTask 5.5: 实现运行完成后自动保存报告

- [x] Task 6: 实现游戏画面预览
  - [x] SubTask 6.1: 创建 `td_executor/ui/preview_tab.py`，实现 PreviewTab 类
  - [x] SubTask 6.2: 实现截图显示（Canvas + PhotoImage）
  - [x] SubTask 6.3: 实现自动刷新（执行期间每 2 秒）
  - [x] SubTask 6.4: 实现手动刷新按钮
  - [x] SubTask 6.5: 实现格子标注叠加（slot 位置红色圆点 + 标签）
  - [x] SubTask 6.6: 实现标注开关复选框
  - [x] SubTask 6.7: 实现截图保存功能
  - [x] SubTask 6.8: 实现 Pillow 不可用时的降级提示

- [x] Task 7: 更新 CLI 和依赖配置
  - [x] SubTask 7.1: 在 cli.py 中新增 gui 命令
  - [x] SubTask 7.2: 在 pyproject.toml 中新增 ui 可选依赖组（Pillow>=10.0.0）

- [x] Task 8: 编写测试
  - [x] SubTask 8.1: 测试事件系统（事件创建、队列通信）
  - [x] SubTask 8.2: 测试 executor_bridge（线程安全、停止标志）
  - [x] SubTask 8.3: 测试 CLI gui 命令入口

# Task Dependencies

- Task 2 依赖 Task 1（需要事件系统和桥接模块）
- Task 3 依赖 Task 1 和 Task 2（需要事件系统和主窗口）
- Task 4 依赖 Task 1 和 Task 2（需要桥接模块和主窗口）
- Task 5 依赖 Task 2（需要主窗口）
- Task 6 依赖 Task 2（需要主窗口）
- Task 3、4、5、6 可并行开发
- Task 7 依赖 Task 2（需要 launch 函数）
- Task 8 依赖 Task 1~7
