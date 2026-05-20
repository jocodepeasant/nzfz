# Script 模块 — 脚本加载与校验

脚本模块负责从磁盘加载 JSON 脚本文件，并根据共享的 JSON Schema 进行结构校验。

## 模块结构

```
script/
├── __init__.py      # 模块导出
├── load.py          # 脚本加载
└── validate.py      # 脚本校验
```

---

## load.py — 脚本加载

### 概述

从磁盘读取 JSON 脚本文件并解析为 Python 字典。

### 核心函数

#### `load_script_file(path: Path) -> dict[str, Any]`

**参数：**
- `path` — 脚本文件路径

**返回值：** 解析后的脚本字典

**校验规则：**
- 文件必须为 UTF-8 编码
- JSON 根节点必须是 `object`（`dict`），否则抛出 `ValueError`

**异常：**
- `FileNotFoundError` — 文件不存在
- `json.JSONDecodeError` — JSON 格式错误
- `ValueError` — 根节点不是 object

---

## validate.py — 脚本校验

### 概述

根据共享的 JSON Schema（`tower_defense_script_v1.schema.json`）校验脚本数据结构的合法性。

### Schema 文件位置

```
<schemas>/tower_defense_script_v1.schema.json
```

路径基于项目根目录的 `schemas/` 目录，通过 `__file__` 向上 4 级定位。

### 核心函数

#### `validate_script_data(data: dict[str, Any]) -> list[dict[str, str]]`

**参数：**
- `data` — 脚本字典（由 `load_script_file` 返回）

**返回值：** 错误列表，每项包含：
```python
{
    "path": "/waves/0/actions/1/type",  # JSON 路径
    "message": "..."                     # 错误描述
}
```

**校验流程：**
1. 定位 Schema 文件，若不存在则返回错误
2. 使用 `jsonschema.Draft202012Validator` 进行校验
3. 收集所有校验错误，转换为路径+消息格式

**注意：** 返回空列表表示校验通过。

#### `assert_valid(data: dict[str, Any]) -> None`

断言脚本有效。校验失败时抛出 `ValueError`，包含第一个错误信息。
