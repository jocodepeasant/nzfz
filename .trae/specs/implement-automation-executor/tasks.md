# Tasks

- [ ] Task 1: 实现 GameState 状态管理
  - [ ] SubTask 1.1: 定义 GameState 数据类，包含 wave、resource、core_hp、in_map_ui、current_region_id、executed_waves 等字段
  - [ ] SubTask 1.2: 实现状态更新方法 update_wave / update_resource / update_core_hp / update_map_ui / update_region
  - [ ] SubTask 1.3: 实现状态变化检测，wave 变化时触发回调通知
  - [ ] SubTask 1.4: 编写 GameState 单元测试

- [ ] Task 2: 实现 InputAdapter 输入抽象层
  - [ ] SubTask 2.1: 定义 InputAdapter 抽象基类（click / key_press / key_hold / drag / scroll）
  - [ ] SubTask 2.2: 实现 PynputAdapter（默认），使用 pynput 底层输入模拟，考虑反作弊兼容
  - [ ] SubTask 2.3: 实现 PyautoguiAdapter 备选方案
  - [ ] SubTask 2.4: 编写 InputAdapter 单元测试（mock 模式）

- [ ] Task 3: 实现 ScreenCapture 截图抽象层
  - [ ] SubTask 3.1: 定义 ScreenCapture 抽象基类（capture_full / capture_roi）
  - [ ] SubTask 3.2: 实现 MssCapture（默认），使用 mss 截取窗口区域
  - [ ] SubTask 3.3: 实现 DxcamCapture 备选方案
  - [ ] SubTask 3.4: 编写 ScreenCapture 单元测试

- [ ] Task 4: 实现 WindowManager 游戏窗口管理
  - [ ] SubTask 4.1: 实现 find_game_window，通过窗口标题定位游戏窗口
  - [ ] SubTask 4.2: 实现 get_window_rect，返回 left/top/width/height
  - [ ] SubTask 4.3: 实现 bring_to_front，将窗口前置
  - [ ] SubTask 4.4: 编写 WindowManager 单元测试

- [ ] Task 5: 实现 OCREngine OCR 引擎
  - [ ] SubTask 5.1: 定义 OCREngine 抽象基类（read_wave / read_resource / read_core_hp）
  - [ ] SubTask 5.2: 实现轻量数字识别方案（模板匹配+数字分割）
  - [ ] SubTask 5.3: 实现多帧投票机制，提高识别准确率
  - [ ] SubTask 5.4: 实现 PaddleOCR 适配器（可选依赖）
  - [ ] SubTask 5.5: 编写 OCREngine 单元测试

- [ ] Task 6: 实现 VisionDetector 视觉检测器
  - [ ] SubTask 6.1: 实现 match_template 模板匹配
  - [ ] SubTask 6.2: 实现 color_region_check 颜色区域检测
  - [ ] SubTask 6.3: 实现 detect_map_ui 检测是否在地图界面
  - [ ] SubTask 6.4: 实现 detect_slot_state 检测格子状态（空/占用/等级）
  - [ ] SubTask 6.5: 编写 VisionDetector 单元测试

- [ ] Task 7: 实现 ConditionEngine 条件判断引擎
  - [ ] SubTask 7.1: 实现 eval_conditions，遍历 conditions 字典评估所有条件
  - [ ] SubTask 7.2: 实现 resource_gte 条件判断
  - [ ] SubTask 7.3: 实现 slot_empty / slot_occupied 条件判断
  - [ ] SubTask 7.4: 实现 wave_gte 条件判断
  - [ ] SubTask 7.5: 实现 trap_level_lt 条件判断
  - [ ] SubTask 7.6: 编写 ConditionEngine 单元测试

- [ ] Task 8: 实现 Navigator 地图区域导航
  - [ ] SubTask 8.1: 实现 pan_to_region，根据 region 的 enter_actions 执行 pan_map 拖拽序列
  - [ ] SubTask 8.2: 实现 reset_to_origin，关闭地图再重新打开回原点
  - [ ] SubTask 8.3: 实现 ensure_map_ui，检测并打开地图界面
  - [ ] SubTask 8.4: 编写 Navigator 单元测试

- [ ] Task 9: 实现 SlotLocator 格子定位
  - [ ] SubTask 9.1: 实现 locate_slot，根据 slot.position 比例坐标计算像素坐标
  - [ ] SubTask 9.2: 实现 micro_adjust，按 pattern 生成偏移坐标序列（cross_5_points 等）
  - [ ] SubTask 9.3: 编写 SlotLocator 单元测试

- [ ] Task 10: 实现 ActionExecutor 动作执行器
  - [ ] SubTask 10.1: 实现 execute_action 分发器，根据 action.type 路由到对应处理函数
  - [ ] SubTask 10.2: 实现 place_trap 流程（选陷阱→导航→点击→等待→验证）
  - [ ] SubTask 10.3: 实现 upgrade_trap 流程（长按升级键→等待→验证）
  - [ ] SubTask 10.4: 实现 remove_trap 流程（导航→执行拆除步骤→等待→验证）
  - [ ] SubTask 10.5: 实现 log 动作
  - [ ] SubTask 10.6: 编写 ActionExecutor 单元测试

- [ ] Task 11: 实现 RetryManager 重试管理器
  - [ ] SubTask 11.1: 实现 execute_with_retry，包装动作执行+重试逻辑
  - [ ] SubTask 11.2: 实现 reset_view_before_retry，重试前回原点重新导航
  - [ ] SubTask 11.3: 实现 micro_adjust_on_retry，重试时使用微调坐标
  - [ ] SubTask 11.4: 编写 RetryManager 单元测试

- [ ] Task 12: 实现 ExecutorContext 编排上下文
  - [ ] SubTask 12.1: 定义 ExecutorContext 类，持有 script / state / window_rect / input / capture / ocr / detector / navigator / slot_locator / action_executor / retry_manager / report_manager
  - [ ] SubTask 12.2: 实现 from_script 工厂方法，根据脚本和选项创建完整上下文
  - [ ] SubTask 12.3: 编写 ExecutorContext 单元测试

- [ ] Task 13: 实现主执行循环
  - [ ] SubTask 13.1: 实现 run_loop 主循环（固定间隔轮询+定向ROI扫描）
  - [ ] SubTask 13.2: 实现波次轮询逻辑（固定间隔1s扫描 wave ROI 区域）
  - [ ] SubTask 13.3: 实现波次动作序列执行
  - [ ] SubTask 13.4: 实现动作执行中定向ROI扫描（资源/格子状态等）
  - [ ] SubTask 13.5: 实现结算检测（胜利/失败/异常）
  - [ ] SubTask 13.6: 实现超时保护
  - [ ] SubTask 13.7: 实现 dry-run 模拟执行模式
  - [ ] SubTask 13.8: 编写主循环集成测试

- [ ] Task 14: 实现 ReportManager 报告管理器
  - [ ] SubTask 14.1: 实现动作结果记录（类型/名称/结果/重试次数/耗时）
  - [ ] SubTask 14.2: 实现单局 JSON 报告生成
  - [ ] SubTask 14.3: 编写 ReportManager 单元测试

- [ ] Task 15: 实现 BatchRunner 批量跑局
  - [ ] SubTask 15.1: 实现批量执行循环，每局结束后等待重新进入对局
  - [ ] SubTask 15.2: 编写 BatchRunner 单元测试

- [ ] Task 16: 扩展 CLI 命令
  - [ ] SubTask 16.1: 扩展 run 命令，接入完整执行流程
  - [ ] SubTask 16.2: 添加 --count 参数支持批量跑局
  - [ ] SubTask 16.3: 添加 --report-dir 参数指定报告输出目录
  - [ ] SubTask 16.4: 完善 --dry-run 模拟执行输出
  - [ ] SubTask 16.5: 编写 CLI 集成测试

- [ ] Task 17: 更新 pyproject.toml 依赖
  - [ ] SubTask 17.1: 将 pynput 从 optional 移至 runtime 依赖组
  - [ ] SubTask 17.2: 确认所有新增依赖正确声明

# Task Dependencies

- Task 7 (ConditionEngine) depends on Task 1 (GameState)
- Task 8 (Navigator) depends on Task 2 (InputAdapter), Task 6 (VisionDetector)
- Task 9 (SlotLocator) depends on Task 4 (WindowManager)
- Task 10 (ActionExecutor) depends on Task 2 (InputAdapter), Task 7 (ConditionEngine), Task 8 (Navigator), Task 9 (SlotLocator), Task 11 (RetryManager)
- Task 11 (RetryManager) depends on Task 8 (Navigator), Task 9 (SlotLocator)
- Task 12 (ExecutorContext) depends on Task 1-11 全部
- Task 13 (主循环) depends on Task 12 (ExecutorContext)
- Task 14 (ReportManager) 无强依赖，可与 Task 7-11 并行
- Task 15 (BatchRunner) depends on Task 13 (主循环)
- Task 16 (CLI) depends on Task 13 (主循环), Task 15 (BatchRunner)
- Task 17 (依赖更新) 无强依赖，可最先执行

# Parallelizable Work

- Task 1 (GameState), Task 2 (InputAdapter), Task 3 (ScreenCapture), Task 4 (WindowManager), Task 17 (依赖更新) 可并行
- Task 5 (OCREngine), Task 6 (VisionDetector) 可并行
- Task 7 (ConditionEngine) 在 Task 1 完成后可独立推进
- Task 14 (ReportManager) 可与 Task 7-11 并行
