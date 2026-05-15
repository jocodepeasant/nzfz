# 自动化执行器核心实现 Spec

## Why

自动化执行器当前仅有脚本加载/校验和坐标转换三个模块有实际实现，其余全部为占位桩函数。需要填充核心执行逻辑，使其能够读取脚本 JSON 并在游戏对局内自动执行塔防通关操作。

## What Changes

- 新增 `ExecutorContext` 编排上下文类，集中管理执行过程中的共享状态
- 完善 `GameState` 状态管理，支持波次/资源/血量/UI状态追踪与状态变化事件
- 实现 `ConditionEngine` 条件判断引擎，支持所有条件类型
- 实现 `RetryManager` 重试管理器，支持重试策略与视图重置
- 实现 `Navigator` 地图区域导航，支持 pan_map 拖拽与回原点
- 实现 `SlotLocator` 格子定位，支持比例坐标转换与微调
- 实现 `ActionExecutor` 动作执行器，支持 place_trap / upgrade_trap / remove_trap / log
- 实现 `InputAdapter` 输入抽象层，默认 pynput，可切换 pyautogui
- 实现 `ScreenCapture` 截图抽象层，默认 mss，可切换 dxcam
- 实现 `WindowManager` 游戏窗口定位与管理
- 实现 `OCREngine` OCR 引擎，轻量优先（模板匹配+数字识别），可选 PaddleOCR
- 实现 `VisionDetector` 视觉检测器，支持模板匹配与颜色区域检测
- 实现主执行循环（固定间隔轮询+定向ROI扫描），支持 dry-run 模拟执行
- 实现 `ReportManager` 单局日志与报告生成
- 实现 `BatchRunner` 批量跑局
- 扩展 CLI `run` 命令，接入完整执行流程

## Impact

- Affected specs: 无前置 spec
- Affected code:
  - `automation-executor/src/td_executor/` 全部模块
  - `automation-executor/pyproject.toml` 依赖更新

## ADDED Requirements

### Requirement: ExecutorContext 编排上下文

系统 SHALL 提供 `ExecutorContext` 类，作为执行过程的中央上下文对象，持有脚本数据、游戏状态、窗口信息、当前区域、输入适配器、截图适配器等共享资源，所有模块通过 context 协作。

#### Scenario: 创建上下文
- **WHEN** 用户执行 `td-executor run <script.json>`
- **THEN** 系统加载脚本、校验合法性、创建 ExecutorContext 实例，初始化所有子模块

#### Scenario: dry-run 模式
- **WHEN** 用户执行 `td-executor run <script.json> --dry-run`
- **THEN** 系统模拟执行完整流程（状态变化、条件判断、动作编排），但不进行实际截图/输入操作，输出模拟执行日志

### Requirement: GameState 状态管理

系统 SHALL 提供 `GameState` 类，追踪当前波次、资源数值、核心血量、是否在地图界面、当前所在区域、已执行波次集合等状态，并支持状态变化检测与事件通知。

#### Scenario: 波次变化检测
- **WHEN** OCR 识别到波次数字从 N 变为 N+1
- **THEN** GameState 触发 wave_changed 事件，主循环据此进入对应波次的动作执行

#### Scenario: 资源更新
- **WHEN** OCR 识别到资源数值
- **THEN** GameState 更新当前资源值，条件引擎可据此判断 resource_gte

### Requirement: 固定间隔轮询+定向ROI扫描主循环

系统 SHALL 实现固定间隔轮询的主执行循环：以固定间隔（默认1s）持续扫描波次 ROI 区域的数字，检测到波次变化时进入对应波次的动作执行；动作执行过程中仅对需要的 ROI 做定向扫描（资源/格子状态），不做全屏识别。波次图标位置固定，因此只需扫描固定 ROI 区域即可。

#### Scenario: 轮询检测波次
- **WHEN** 当前波次的所有动作已执行完毕或等待下一波
- **THEN** 系统以固定间隔（默认1s）扫描 wave ROI 区域识别波次数字，直到检测到波次变化

#### Scenario: 波次触发动作执行
- **WHEN** 检测到波次变化匹配某个 wave 的 trigger
- **THEN** 系统立即进入该波次的动作序列执行

#### Scenario: 动作执行中定向扫描
- **WHEN** 动作执行需要判断条件或验证结果
- **THEN** 系统仅扫描对应 ROI 区域（如 resource ROI 判断资源、slot check_area 验证格子状态），不做全屏识别

#### Scenario: 超时保护
- **WHEN** 执行时间超过 runtime.max_run_minutes
- **THEN** 系统终止执行并生成超时报告

### Requirement: ConditionEngine 条件判断引擎

系统 SHALL 实现 `ConditionEngine`，支持以下条件类型：
- `resource_gte`：当前资源 ≥ 指定值
- `slot_empty`：指定格子为空
- `slot_occupied`：指定格子已占用
- `wave_gte`：当前波次 ≥ 指定值
- `trap_level_lt`：指定陷阱等级 < 指定值

#### Scenario: 条件满足
- **WHEN** 动作的所有 conditions 均评估为 True
- **THEN** 允许执行该动作

#### Scenario: 条件不满足 - 等待策略
- **WHEN** 条件不满足且 on_condition_failed.policy 为 "wait"
- **THEN** 系统在 timeout_ms 内等待条件满足，超时后按 then 策略处理

#### Scenario: 条件不满足 - 跳过策略
- **WHEN** 条件不满足且 on_condition_failed.policy 为 "skip"
- **THEN** 跳过该动作，记录日志

### Requirement: RetryManager 重试管理器

系统 SHALL 实现 `RetryManager`，根据 retry 配置处理动作失败重试，支持：
- `max_count`：最大重试次数
- `interval_ms`：重试间隔
- `reset_view_before_retry`：重试前回原点重新导航
- `micro_adjust_on_retry`：重试时微调点击位置

#### Scenario: 重试成功
- **WHEN** 动作执行失败，重试次数未达上限，重试后验证通过
- **THEN** 记录重试日志，继续后续动作

#### Scenario: 重试耗尽
- **WHEN** 动作执行失败且重试次数已达上限
- **THEN** 按 on_fail.policy 处理（skip / abort）

### Requirement: InputAdapter 输入抽象层

系统 SHALL 提供 `InputAdapter` 抽象接口，支持键鼠操作（点击、按键、长按、拖拽），默认使用 pynput 实现（游戏兼容性更好），可切换为 pyautogui。需考虑游戏反作弊兼容性，使用底层输入模拟。

#### Scenario: 点击格子
- **WHEN** ActionExecutor 需要点击某个 slot 位置
- **THEN** InputAdapter 在目标像素坐标执行点击操作

#### Scenario: 长按升级
- **WHEN** ActionExecutor 需要长按按键升级陷阱
- **THEN** InputAdapter 执行指定时长的按键按住操作

#### Scenario: 拖拽地图
- **WHEN** Navigator 需要拖拽地图进入区域
- **THEN** InputAdapter 执行从起点到终点的拖拽操作

### Requirement: ScreenCapture 截图抽象层

系统 SHALL 提供 `ScreenCapture` 抽象接口，默认使用 mss 实现，可切换为 dxcam。支持截取指定窗口区域。

#### Scenario: 截取游戏画面
- **WHEN** 主循环需要识别游戏状态
- **THEN** ScreenCapture 截取游戏窗口画面并返回 numpy 数组

#### Scenario: 截取 ROI 区域
- **WHEN** OCR/Detector 只需要识别特定区域
- **THEN** ScreenCapture 截取指定 ROI 区域

### Requirement: WindowManager 游戏窗口管理

系统 SHALL 实现 `WindowManager`，支持定位游戏窗口、获取窗口位置与尺寸、将窗口前置。

#### Scenario: 定位游戏窗口
- **WHEN** 执行器启动
- **THEN** WindowManager 通过窗口标题定位游戏窗口，获取 left/top/width/height

#### Scenario: 窗口未找到
- **WHEN** 无法定位游戏窗口
- **THEN** 报错退出并提示用户启动游戏

### Requirement: OCREngine OCR 引擎

系统 SHALL 实现 `OCREngine`，优先使用轻量方案（模板匹配+数字识别）识别波次数字和资源数值，可选接入 PaddleOCR。支持多帧投票提高准确率。

#### Scenario: 识别波次数字
- **WHEN** 主循环需要判断当前波次
- **THEN** OCREngine 截取 wave ROI 区域，通过多帧投票识别波次数字

#### Scenario: 识别资源数值
- **WHEN** 条件引擎需要判断资源是否充足
- **THEN** OCREngine 截取 resource ROI 区域，识别资源数值

### Requirement: VisionDetector 视觉检测器

系统 SHALL 实现 `VisionDetector`，支持 OpenCV 模板匹配和颜色区域检测，用于识别地图界面指示器、格子状态、放置错误提示等。

#### Scenario: 检测地图界面
- **WHEN** 需要判断是否在地图界面
- **THEN** VisionDetector 在 map_ui_indicator ROI 区域进行模板匹配

#### Scenario: 检测格子状态
- **WHEN** 需要验证 slot 是否为空/已占用
- **THEN** VisionDetector 在 slot verify.check_area 区域检测状态

### Requirement: Navigator 地图区域导航

系统 SHALL 实现 `Navigator`，支持通过 pan_map 拖拽动作进入指定区域，支持回原点（关闭地图再重新打开）。

#### Scenario: 导航到目标区域
- **WHEN** 动作需要操作某个 region 内的 slot
- **THEN** Navigator 执行该 region 的 enter_actions 序列（pan_map 拖拽）

#### Scenario: 回原点
- **WHEN** 需要重置视野或重试前需要回原点
- **THEN** Navigator 关闭地图（按 O），重新打开地图（按 O），等待稳定

### Requirement: SlotLocator 格子定位

系统 SHALL 实现 `SlotLocator`，根据 slot 配置的比例坐标计算实际像素坐标，支持微调模式（cross_5_points 等模式）。

#### Scenario: 定位格子
- **WHEN** ActionExecutor 需要点击某个 slot
- **THEN** SlotLocator 根据 slot.position 的比例坐标和当前窗口尺寸计算像素坐标

#### Scenario: 微调定位
- **WHEN** 首次点击失败且 micro_adjust_on_retry 为 True
- **THEN** SlotLocator 按 micro_adjust_pattern 生成偏移坐标序列

### Requirement: ActionExecutor 动作执行器

系统 SHALL 实现 `ActionExecutor`，支持四种动作类型：
- `place_trap`：选择陷阱→点击格子→验证放置
- `upgrade_trap`：长按升级键→验证升级
- `remove_trap`：执行拆除步骤→验证拆除
- `log`：记录日志消息

每个动作执行前检查 conditions，失败后按 retry 重试，重试耗尽按 on_fail 处理。

#### Scenario: 放置陷阱成功
- **WHEN** 执行 place_trap 动作，条件满足
- **THEN** 选择陷阱按键→导航到 slot 区域→点击 slot 位置→等待 wait_after_place_ms→验证 slot_has_trap

#### Scenario: 升级陷阱成功
- **WHEN** 执行 upgrade_trap 动作，条件满足
- **THEN** 长按 upgrade_key 指定时长→等待 wait_after_upgrade_ms→验证 trap_level_gte

#### Scenario: 拆除陷阱成功
- **WHEN** 执行 remove_trap 动作，条件满足
- **THEN** 导航到 slot 区域→执行拆除步骤→等待 wait_after_remove_ms→验证 slot_empty

### Requirement: ReportManager 报告管理器

系统 SHALL 实现 `ReportManager`，记录每个动作的执行结果（成功/失败/重试/跳过），生成单局 JSON 报告。

#### Scenario: 记录动作结果
- **WHEN** 每个动作执行完成（无论成功/失败/跳过）
- **THEN** ReportManager 记录动作类型、名称、结果、重试次数、耗时

#### Scenario: 生成单局报告
- **WHEN** 对局结束（胜利/失败/超时）
- **THEN** ReportManager 生成 JSON 格式的单局报告文件

### Requirement: BatchRunner 批量跑局

系统 SHALL 实现 `BatchRunner`，支持使用同一脚本连续跑多局，每局结束后等待重新进入对局。

#### Scenario: 批量执行
- **WHEN** 用户指定跑 N 局
- **THEN** 系统连续执行 N 局，每局生成独立报告

### Requirement: CLI 扩展

系统 SHALL 扩展 CLI `run` 命令，接入完整执行流程，支持 `--dry-run`、`--count`（批量局数）、`--report-dir`（报告输出目录）等参数。

#### Scenario: 实际执行
- **WHEN** 用户执行 `td-executor run <script.json>`
- **THEN** 系统加载脚本、校验、定位窗口、进入主循环执行

#### Scenario: dry-run 模拟
- **WHEN** 用户执行 `td-executor run <script.json> --dry-run`
- **THEN** 系统模拟执行完整流程，输出模拟日志，不操作游戏
