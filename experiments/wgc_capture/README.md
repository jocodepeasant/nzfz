# P2-03A Windows Graphics Capture 技术验证

本目录用于 P2-03 阶段 A：在接入正式后端前，独立验证 Python 技术栈能否通过 `hwnd` 使用 WGC 获取窗口图像。

## 环境要求

- Windows 10 1903+（Build 18362+）
- Python 3.10+
- 支持 DirectX 11 的 GPU

## 安装依赖

```bash
pip install -r experiments/wgc_capture/requirements.txt
```

或从仓库根目录：

```bash
pip install -e "./executor[wgc]"
```

## 运行验证

按窗口句柄：

```bash
python experiments/wgc_capture/wgc_probe.py --hwnd 123456
```

按标题关键词：

```bash
python experiments/wgc_capture/wgc_probe.py --title "记事本"
```

输出 PNG 默认保存到 `experiments/wgc_capture/output/`。

## 建议验证场景

| 场景 | 操作 | 期望 |
|------|------|------|
| 普通窗口无遮挡 | 对可见窗口运行 probe | PNG 成功生成 |
| 普通窗口被遮挡 | 用其他窗口盖住目标后 capture | PNG 仍为目标窗口内容 |
| 游戏窗口无遮挡 | 连接游戏后 probe | 记录成功/失败 |
| 游戏窗口被遮挡 | 遮挡后 probe | 记录是否为核心目标能力 |
| 游戏窗口非前台 | 切到其他窗口后 probe | 记录后台捕获能力 |
| 窗口最小化 | `--hwnd` 指向最小化窗口 | 脚本报错退出 |
| hwnd 无效 | `--hwnd 0` | 明确错误 |

## 验证结论（基线环境）

记录于实现时本地探测（开发机 Windows，Python 3.12）：

| 项目 | 结论 |
|------|------|
| 依赖方案 | `winsdk` + `pywin32` |
| 普通可见窗口 WGC 单帧 | 成功（可生成 PNG） |
| PIL 转换 | 成功（RGBA → RGB 保存） |
| 是否适合接入正式后端 | 是 |
| 被遮挡普通窗口 | 需手动遮挡后复测并更新本表 |
| 目标游戏窗口 | 需连接实际游戏后复测并更新本表 |
| 最小化窗口 | 预期失败（与 P2-03 规范一致） |
| DPI 125%/150% | 正式后端通过比例裁剪处理，复杂场景待单独验证 |

## 正式后端

验证通过后，捕获逻辑封装在：

- [`nzfz_executor/core/wgc_capture.py`](../../nzfz_executor/core/wgc_capture.py)
- [`nzfz_executor/core/screenshot_manager.py`](../../nzfz_executor/core/screenshot_manager.py) 中的 `WindowsGraphicsCaptureBackend`

`CaptureBackendType.AUTO` 策略：优先 WGC，失败回退 `ScreenCaptureBackend`。
