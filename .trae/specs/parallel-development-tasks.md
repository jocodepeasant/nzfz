# 自动化执行器 — 并行开发任务跟踪

> 基于 `tower_defense_automation_design_v1.md` §10.2 执行器团队优先级，跟踪各模块开发进度。

## 任务总览

| 编号 | 模块 | 优先级 | 状态 | 对应 Spec |
|------|------|--------|------|-----------|
| T01 | JSON 加载与校验 | P0 | ✅ 已完成 | — (骨架内置) |
| T02 | 屏幕采集 (Screen Capture) | P0 | ✅ 已完成 | `implement-screen-capture` |
| T03 | 重试框架 (Retry Framework) | P0 | ✅ 已完成 | `implement-retry-framework` |
| T04 | 游戏窗口识别与管理 | P1 | 🔲 未开始 | — |
| T05 | OCR 识别波次、资源 | P1 | 🔲 未开始 | — |
| T06 | 地图界面判断与导航 | P1 | 🔲 未开始 | — |
| T07 | 动作执行引擎 (place/upgrade/remove) | P1 | 🔲 未开始 | — |
| T08 | 条件引擎 | P1 | 🔲 未开始 | — |
| T09 | 单局日志与报告 | P2 | 🔲 未开始 | — |
| T10 | 批量跑固定脚本 | P2 | 🔲 未开始 | — |

---

## 已完成任务详情

### T01 — JSON 加载与校验
- **状态**: ✅ 已完成（骨架阶段内置）
- **实现文件**:
  - `automation-executor/src/td_executor/script/load.py` — 加载脚本 JSON
  - `automation-executor/src/td_executor/script/validate.py` — 基于 jsonschema 校验
  - `automation-executor/src/td_executor/cli.py` — `validate` / `run --dry-run` 命令
- **依赖**: `schemas/tower_defense_script_v1.schema.json`

### T02 — 屏幕采集 (Screen Capture)
- **状态**: ✅ 已完成
- **Spec**: `.trae/specs/implement-screen-capture/`
- **实现文件**:
  - `automation-executor/src/td_executor/runtime/capture.py` — ScreenCapture 类，支持 mss/dxcam 后端
  - `automation-executor/src/td_executor/runtime/__init__.py` — 导出更新
- **测试**: `automation-executor/tests/test_capture.py` (164 行)
- **关键能力**:
  - mss 后端全屏/区域截图，返回 BGR/RGB numpy ndarray
  - dxcam 后端（条件导入，不可用抛 ImportError）
  - 上下文管理器、lazy init、close 后 RuntimeError 保护

### T03 — 重试框架 (Retry Framework)
- **状态**: ✅ 已完成
- **Spec**: `.trae/specs/implement-retry-framework/`
- **实现文件**:
  - `automation-executor/src/td_executor/engine/retry.py` — RetryManager + 配置数据类
  - `automation-executor/src/td_executor/engine/__init__.py` — 导出更新
- **测试**: `automation-executor/tests/test_retry.py` (48 项测试全部通过)
- **关键能力**:
  - RetryConfig / OnConditionFailedConfig / OnFailConfig 数据类，支持 from_dict 从脚本 JSON 构造
  - RetryManager 配置合并（动作级覆盖运行时默认值）
  - wait_for_condition 条件等待轮询（wait/skip 策略）
  - execute_with_retry 带重试的动作执行（回调、异常捕获、on_fail 降级）

---

## 未完成任务详情

### T04 — 游戏窗口识别与管理
- **优先级**: P1
- **当前状态**: 占位 (`runtime/window.py` — `raise NotImplementedError`)
- **依赖**: pywin32 (Windows) / 其他平台窗口管理方案
- **关键能力**:
  - 定位游戏窗口句柄
  - 获取窗口位置与尺寸（供坐标转换和截图使用）
  - 窗口前置激活
- **前置依赖**: 无

### T05 — OCR 识别波次、资源
- **优先级**: P1
- **当前状态**: 占位 (`vision/ocr.py` — `raise NotImplementedError`)
- **依赖**: PaddleOCR / EasyOCR, T02 (屏幕采集)
- **关键能力**:
  - 从 ROI 区域识别波次数字
  - 从 ROI 区域识别资源数量
  - 从 ROI 区域识别核心血量
  - 多帧投票提高识别准确率
- **前置依赖**: T02

### T06 — 地图界面判断与导航
- **优先级**: P1
- **当前状态**: 占位 (`engine/navigator.py` — `raise NotImplementedError`, `vision/detector.py` — `raise NotImplementedError`)
- **依赖**: T02 (截图), T04 (窗口)
- **关键能力**:
  - 判断是否在地图界面 (map_ui_indicator)
  - 按 O 打开/关闭地图
  - 回到 origin 视野
  - pan_to_region 拖拽导航
- **前置依赖**: T02, T04

### T07 — 动作执行引擎 (place/upgrade/remove)
- **优先级**: P1
- **当前状态**: 占位 (`engine/action.py` — `raise NotImplementedError`, `engine/slot.py` — `raise NotImplementedError`)
- **依赖**: T02, T04, T06, T08
- **关键能力**:
  - place_trap: 选择陷阱 → 点击格子 → 验证放置
  - upgrade_trap: 长按升级键 → 验证等级
  - remove_trap: 执行拆除 → 验证清空
  - 与 T03 (重试框架) 集成
- **前置依赖**: T02, T04, T06, T08

### T08 — 条件引擎
- **优先级**: P1
- **当前状态**: 占位 (`engine/condition.py` — `raise NotImplementedError`)
- **依赖**: T05 (OCR 识别资源/波次)
- **关键能力**:
  - resource_gte: 资源是否 ≥ 阈值
  - slot_empty / slot_occupied: 格子状态判断
  - wave_eq / wave_gte: 波次条件
  - trap_level_lt: 陷阱等级条件
  - 与 T03 (on_condition_failed) 集成
- **前置依赖**: T05

### T09 — 单局日志与报告
- **优先级**: P2
- **当前状态**: 占位 (`engine/report.py` — `raise NotImplementedError`)
- **依赖**: 无强依赖，可随时开发
- **关键能力**:
  - 记录每步动作结果
  - 生成 JSON/CSV/HTML 报告
- **前置依赖**: 无

### T10 — 批量跑固定脚本
- **优先级**: P2
- **当前状态**: 占位 (`engine/batch.py` — `raise NotImplementedError`)
- **依赖**: T07 (动作执行)
- **关键能力**:
  - 顺序执行多个脚本
  - 统计成功/失败次数
- **前置依赖**: T07

---

## 依赖关系图

```
T01 (JSON加载) ───────────────────────────────────────────── ✅
T02 (屏幕采集) ─────┬────────────────────────────────────── ✅
                    │
T04 (窗口管理) ─────┼────┬────────────────────────────────── 🔲
                    │    │
T05 (OCR识别) ──────┼────┼────┬───────────────────────────── 🔲
                    │    │    │
T06 (地图导航) ─────┼────┼────┼────┬──────────────────────── 🔲
                    │    │    │    │
T08 (条件引擎) ─────┼────┼────┼────┼────┬─────────────────── 🔲
                    │    │    │    │    │
T03 (重试框架) ─────┼────┼────┼────┼────┼────┬────────────── ✅
                    │    │    │    │    │    │
T07 (动作执行) ─────┼────┼────┼────┼────┼────┼────┬───────── 🔲
                    │    │    │    │    │    │    │
T09 (日志报告) ─────┼────┼────┼────┼────┼────┼────┼──────── 🔲
                    │    │    │    │    │    │    │
T10 (批量跑局) ─────┼────┼────┼────┼────┼────┼────┼──────── 🔲
```

## 建议的下一批并行任务

以下任务可并行启动（无相互依赖）：
- **T04** (游戏窗口管理) — 无前置依赖
- **T05** (OCR 识别) — 依赖 T02 ✅

完成后可启动：
- **T06** (地图导航) + **T08** (条件引擎) — 可并行
- 最终集成 **T07** (动作执行)
