# Tasks

- [ ] Task 1: 实现 CaptureConfig 数据类和 CaptureBackend 枚举
  - [ ] 1.1: 在 capture.py 中定义 CaptureBackend 枚举（mss / dxcam）
  - [ ] 1.2: 定义 CaptureConfig dataclass（backend, region, output_format 字段，含默认值）
- [ ] Task 2: 实现 ScreenCapture 类核心逻辑
  - [ ] 2.1: 实现 `__init__` 接收 CaptureConfig 或关键字参数
  - [ ] 2.2: 实现 `start()` / `close()` 生命周期方法，管理 mss/dxcam 后端实例
  - [ ] 2.3: 实现上下文管理器 `__enter__` / `__exit__`
  - [ ] 2.4: 实现 mss 后端的 `capture_frame()`：调用 mss 截图 → numpy ndarray BGR
  - [ ] 2.5: 实现指定 region 裁剪逻辑（mss 的 monitor 参数）
  - [ ] 2.6: 实现 dxcam 后端的 `capture_frame()`（条件导入，不可用时抛 ImportError）
  - [ ] 2.7: 实现 lazy init：未 start 时 capture_frame 自动初始化
  - [ ] 2.8: 实现 close 后调用的 RuntimeError 保护
- [ ] Task 3: 更新 runtime/__init__.py 导出
  - [ ] 3.1: 导出 ScreenCapture, CaptureConfig, CaptureBackend
- [ ] Task 4: 确认 pyproject.toml 依赖
  - [ ] 4.1: 确认 mss 已在 [project.optional-dependencies].runtime 中
  - [ ] 4.2: 确认 numpy 已在 [project.optional-dependencies].runtime 中
- [ ] Task 5: 编写单元测试
  - [ ] 5.1: 测试 CaptureConfig 默认值
  - [ ] 5.2: 测试 CaptureBackend 枚举值
  - [ ] 5.3: 测试 mss 后端截图（mock mss 实例）
  - [ ] 5.4: 测试 region 裁剪
  - [ ] 5.5: 测试 dxcam 不可用时 ImportError
  - [ ] 5.6: 测试上下文管理器生命周期
  - [ ] 5.7: 测试 close 后调用 RuntimeError
  - [ ] 5.8: 测试 lazy init 行为

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 5] depends on [Task 2]
- [Task 4] 无依赖，可与 Task 1 并行
