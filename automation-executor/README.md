# 自动化执行器（骨架）

《逆战：未来》塔防脚本执行器 V1 占位工程。协议 JSON 与校验规则见仓库根目录 `schemas/`。

## 环境

- Python 3.10+

## 安装

```bash
cd automation-executor
pip install -e .
```

可选依赖（按文档逐步安装）：

```bash
pip install -e ".[runtime,win,input]"
```

## 命令

校验脚本（使用仓库内 JSON Schema）：

```bash
python -m td_executor validate ../schemas/examples/space_station_normal_baseline_v1.json
```

加载并 dry-run（不操作游戏）：

```bash
python -m td_executor run ../schemas/examples/space_station_normal_baseline_v1.json --dry-run
```

亦可通过入口脚本：

```bash
td-executor validate ../schemas/examples/space_station_normal_baseline_v1.json
```
