# 屏幕采集 (Screen Capture) Spec

## Why
automation-executor 的所有视觉识别能力（OCR 识别波次/资源、模板匹配判断地图界面、槽位状态校验）均依赖屏幕截图。当前 `capture.py` 仅为 `raise NotImplementedError` 的 stub，导致整个视觉管线无法启动，是执行器从"骨架"走向"可运行"的第一步。

## What Changes
- 实现 `capture.py` 中的 `capture_frame()` 函数，支持截取游戏窗口画面并返回图像帧
- 新增 `CaptureBackend` 枚举，支持 `mss`（通用稳定）和 `dxcam`（高频游戏截图）两种后端
- 新增 `CaptureConfig` 数据类，封装截图配置（后端选择、目标窗口区域、缩放等）
- 新增 `ScreenCapture` 类，管理截图生命周期（初始化、截帧、资源释放）
- 支持按窗口区域裁剪截图（与 `runtime/window.py` 的窗口信息配合）
- 在 `pyproject.toml` 的 `[project.optional-dependencies].runtime` 中确认 `mss` 依赖已声明

## Impact
- Affected specs: 视觉识别管线（OCR、模板匹配）的前置依赖
- Affected code:
  - `automation-executor/src/td_executor/runtime/capture.py`（主要修改）
  - `automation-executor/src/td_executor/runtime/__init__.py`（导出更新）
  - `automation-executor/pyproject.toml`（依赖确认）

## ADDED Requirements

### Requirement: Screen Capture Module
系统 SHALL 提供屏幕采集模块，支持截取指定窗口区域的画面并返回图像帧数据。

#### Scenario: 使用 mss 后端截取全屏
- **WHEN** 调用 `ScreenCapture(backend="mss")` 初始化后调用 `capture_frame()`
- **THEN** 返回一个 numpy ndarray（BGR 格式），形状为 (H, W, 3)，dtype 为 uint8

#### Scenario: 使用 mss 后端截取指定窗口区域
- **WHEN** 调用 `ScreenCapture(backend="mss", region={"left": 100, "top": 100, "width": 1920, "height": 1080})` 后调用 `capture_frame()`
- **THEN** 返回仅包含指定区域的 numpy ndarray

#### Scenario: 使用 dxcam 后端截取（可选）
- **WHEN** 调用 `ScreenCapture(backend="dxcam")` 初始化后调用 `capture_frame()`
- **THEN** 返回 numpy ndarray（BGR 格式）；若 dxcam 未安装或不可用，抛出明确错误

#### Scenario: 后端不可用时降级
- **WHEN** 指定 `backend="dxcam"` 但 dxcam 未安装
- **THEN** 抛出 `ImportError` 并提示安装方式

#### Scenario: 资源释放
- **WHEN** `ScreenCapture` 实例作为上下文管理器退出或调用 `close()`
- **THEN** 释放 mss/dxcam 后端资源，后续 `capture_frame()` 抛出 `RuntimeError`

#### Scenario: 未初始化时调用
- **WHEN** 未调用 `__enter__` 或 `start()` 就调用 `capture_frame()`
- **THEN** 自动初始化后执行截图（lazy init）

### Requirement: CaptureConfig 数据类
系统 SHALL 提供 `CaptureConfig` 数据类，封装截图配置参数。

#### Scenario: 默认配置
- **WHEN** 创建 `CaptureConfig()` 不传参数
- **THEN** backend 为 "mss"，region 为 None（全屏），output_format 为 "bgr"

### Requirement: 与坐标转换模块协作
系统 SHALL 支持将截图结果与 `coordinates.ratio_to_pixel()` 配合使用，即截图区域与比例坐标转换的窗口区域一致。

#### Scenario: 截图区域与坐标转换对齐
- **WHEN** 使用窗口信息 (left, top, width, height) 同时设置截图 region 和坐标转换参数
- **THEN** `ratio_to_pixel(left, top, width, height, x_ratio, y_ratio)` 返回的像素坐标落在截图图像的对应位置
