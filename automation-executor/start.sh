#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/.venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON="python3"
    elif command -v python &>/dev/null; then
        PYTHON="python"
    else
        err "未找到 Python，请安装 Python >= 3.10"
        exit 1
    fi

    PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        err "Python 版本过低 ($PY_VERSION)，需要 >= 3.10"
        exit 1
    fi
    ok "Python $PY_VERSION"
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "创建虚拟环境..."
        $PYTHON -m venv "$VENV_DIR"
        ok "虚拟环境已创建: $VENV_DIR"
    fi
}

activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        ok "虚拟环境已激活"
    else
        err "虚拟环境激活失败，请检查 $VENV_DIR"
        exit 1
    fi
}

install_deps() {
    local pkgs_installed=false

    if ! python -c "import td_executor" &>/dev/null; then
        info "安装 td-executor（基础依赖）..."
        pip install -e "$PROJECT_DIR" -q 2>/dev/null
        pkgs_installed=true
    fi

    if ! python -c "import numpy" &>/dev/null; then
        info "安装 runtime 依赖（numpy, opencv, mss）..."
        pip install -e "$PROJECT_DIR[runtime]" -q 2>/dev/null
        pkgs_installed=true
    fi

    if ! python -c "import pynput" &>/dev/null; then
        info "安装 input 依赖（pynput, pyautogui）..."
        pip install -e "$PROJECT_DIR[input]" -q 2>/dev/null
        pkgs_installed=true
    fi

    if ! python -c "import PIL" &>/dev/null; then
        info "安装 ui 依赖（Pillow）..."
        pip install -e "$PROJECT_DIR[ui]" -q 2>/dev/null
        pkgs_installed=true
    fi

    if [ "$pkgs_installed" = true ]; then
        ok "依赖安装完成"
    else
        ok "所有依赖已就绪"
    fi
}

ensure_reports_dir() {
    mkdir -p "$PROJECT_DIR/reports"
}

usage() {
    cat <<EOF
${CYAN}TD Executor - 塔防自动化执行器${NC}

用法: $(basename "$0") <命令> [选项]

命令:
  gui              启动可视化 GUI 界面
  run <脚本路径>   执行自动化脚本
  validate <路径>  校验脚本 JSON 文件
  dry-run <路径>   试运行（仅加载校验，不操作游戏）
  test             运行测试
  help             显示此帮助信息

示例:
  $(basename "$0") gui
  $(basename "$0") run scripts/example.json
  $(basename "$0") validate scripts/example.json
  $(basename "$0") dry-run scripts/example.json
  $(basename "$0") test
EOF
}

run_gui() {
    info "启动 GUI 界面..."
    ensure_reports_dir
    python -m td_executor gui
}

run_script() {
    local script_path="${1:-}"
    if [ -z "$script_path" ]; then
        err "请指定脚本文件路径"
        echo "用法: $(basename "$0") run <脚本路径>"
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        err "脚本文件不存在: $script_path"
        exit 1
    fi
    info "执行脚本: $script_path"
    ensure_reports_dir
    python -m td_executor run "$script_path"
}

run_validate() {
    local script_path="${1:-}"
    if [ -z "$script_path" ]; then
        err "请指定脚本文件路径"
        echo "用法: $(basename "$0") validate <脚本路径>"
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        err "脚本文件不存在: $script_path"
        exit 1
    fi
    python -m td_executor validate "$script_path"
}

run_dry_run() {
    local script_path="${1:-}"
    if [ -z "$script_path" ]; then
        err "请指定脚本文件路径"
        echo "用法: $(basename "$0") dry-run <脚本路径>"
        exit 1
    fi
    if [ ! -f "$script_path" ]; then
        err "脚本文件不存在: $script_path"
        exit 1
    fi
    info "试运行: $script_path"
    python -m td_executor run "$script_path" --dry-run
}

run_tests() {
    info "运行测试..."
    python -m pytest "$PROJECT_DIR/tests" -v
}

main() {
    local cmd="${1:-help}"
    shift || true

    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  TD Executor - 塔防自动化执行器${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""

    check_python
    setup_venv
    activate_venv
    install_deps

    echo ""

    case "$cmd" in
        gui)
            run_gui
            ;;
        run)
            run_script "$@"
            ;;
        validate)
            run_validate "$@"
            ;;
        dry-run)
            run_dry_run "$@"
            ;;
        test)
            run_tests
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            err "未知命令: $cmd"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
