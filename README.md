# 塔防自动化测试系统（仓库骨架）

依据 [`tower_defense_automation_design_v1.md`](tower_defense_automation_design_v1.md) 搭建：**共享 JSON Schema**、**地图配置器（Electron + Vite + React）**、**自动化执行器（Python）**。

## 目录

| 路径 | 说明 |
|------|------|
| [`schemas/`](schemas/) | `tower_defense_script_v1.schema.json` 与示例脚本 |
| [`map-configurator/`](map-configurator/) | 地图配置器：打开 / 校验 / 预览 / 导出 JSON |
| [`automation-executor/`](automation-executor/) | 执行器 CLI：`validate`、`run --dry-run` |

## 地图配置器

```bash
cd map-configurator
npm install
npm run dev
```

从仓库根目录启动时，主进程会读取 `../schemas/tower_defense_script_v1.schema.json` 做 Ajv 校验。

## 自动化执行器

```bash
cd automation-executor
pip install -e .
python -m td_executor validate ../schemas/examples/space_station_normal_baseline_v1.json
python -m td_executor run ../schemas/examples/space_station_normal_baseline_v1.json --dry-run
```

## 设计文档

- [`tower_defense_automation_design_v1.md`](tower_defense_automation_design_v1.md)
