# 地图配置器（骨架）

Electron + Vite + React + TypeScript。开发时从本目录运行 `npm run dev`，主进程使用仓库根下 `schemas/tower_defense_script_v1.schema.json` 校验脚本。

## 命令

- `npm run dev` — 开发调试
- `npm run build` — 构建主进程 / 预加载 / 渲染进程
- `npm run preview` — 预览生产构建
- `npm run pack` — `electron-builder --dir` 打目录包（需已 `build`）
