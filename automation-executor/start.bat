@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_DIR=%SCRIPT_DIR%"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "PYTHON="
set "PY_VERSION="
set "PKGS_INSTALLED=0"

echo ===================================================
echo   TD Executor - 塔防自动化执行器
echo ===================================================
echo.

call :check_python
if !errorlevel! neq 0 goto :error_exit

call :setup_venv
if !errorlevel! neq 0 goto :error_exit

call :activate_venv
if !errorlevel! neq 0 goto :error_exit

call :install_deps
if !errorlevel! neq 0 goto :error_exit

echo.

if "%~1"=="" goto :run_gui
if "%~1"=="gui" goto :run_gui
if "%~1"=="run" goto :run_script
if "%~1"=="validate" goto :run_validate
if "%~1"=="dry-run" goto :run_dry_run
if "%~1"=="test" goto :run_tests
if "%~1"=="help" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help

echo [ERROR] 未知命令: %~1
echo.
goto :show_help

:run_gui
echo [INFO] 启动 GUI 界面...
if not exist "%PROJECT_DIR%\reports" mkdir "%PROJECT_DIR%\reports"
python -m td_executor gui
goto :eof

:run_script
if "%~2"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 run ^<脚本路径^>
    goto :error_exit
)
if not exist "%~2" (
    echo [ERROR] 脚本文件不存在: %~2
    goto :error_exit
)
echo [INFO] 执行脚本: %~2
if not exist "%PROJECT_DIR%\reports" mkdir "%PROJECT_DIR%\reports"
python -m td_executor run "%~2"
goto :eof

:run_validate
if "%~2"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 validate ^<脚本路径^>
    goto :error_exit
)
if not exist "%~2" (
    echo [ERROR] 脚本文件不存在: %~2
    goto :error_exit
)
python -m td_executor validate "%~2"
goto :eof

:run_dry_run
if "%~2"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 dry-run ^<脚本路径^>
    goto :error_exit
)
if not exist "%~2" (
    echo [ERROR] 脚本文件不存在: %~2
    goto :error_exit
)
echo [INFO] 试运行: %~2
python -m td_executor run "%~2" --dry-run
goto :eof

:run_tests
echo [INFO] 运行测试...
python -m pytest "%PROJECT_DIR%\tests" -v
goto :eof

:show_help
echo TD Executor - 塔防自动化执行器
echo.
echo 用法: %~nx0 ^<命令^> [选项]
echo.
echo 命令:
echo   gui              启动可视化 GUI 界面
echo   run ^<脚本路径^>   执行自动化脚本
echo   validate ^<路径^>  校验脚本 JSON 文件
echo   dry-run ^<路径^>   试运行（仅加载校验，不操作游戏）
echo   test             运行测试
echo   help             显示此帮助信息
echo.
echo 示例:
echo   %~nx0 gui
echo   %~nx0 run scripts\example.json
echo   %~nx0 validate scripts\example.json
echo   %~nx0 dry-run scripts\example.json
echo   %~nx0 test
goto :eof

:check_python
where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON=python"
    goto :check_version
)
where python3 >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON=python3"
    goto :check_version
)
echo [ERROR] 未找到 Python，请安装 Python ^>= 3.10
exit /b 1

:check_version
for /f "usebackq tokens=*" %%v in (`!PYTHON! -c "import sys; print(sys.version_info.major)"`) do set "PY_MAJOR=%%v"
for /f "usebackq tokens=*" %%v in (`!PYTHON! -c "import sys; print(sys.version_info.minor)"`) do set "PY_MINOR=%%v"
set "PY_VERSION=!PY_MAJOR!.!PY_MINOR!"

if !PY_MAJOR! lss 3 (
    echo [ERROR] Python 版本过低 ^(!PY_VERSION!^)，需要 ^>= 3.10
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 10 (
    echo [ERROR] Python 版本过低 ^(!PY_VERSION!^)，需要 ^>= 3.10
    exit /b 1
)
echo [OK] Python !PY_VERSION!
exit /b 0

:setup_venv
if exist "%VENV_DIR%" goto :venv_exists
echo [INFO] 创建虚拟环境...
!PYTHON! -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo [ERROR] 虚拟环境创建失败
    exit /b 1
)
echo [OK] 虚拟环境已创建: %VENV_DIR%
:venv_exists
exit /b 0

:activate_venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] 虚拟环境激活失败，请检查 %VENV_DIR%
    exit /b 1
)
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] 虚拟环境已激活
exit /b 0

:install_deps
python -c "import td_executor, numpy, pynput, PIL" >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] 所有依赖已就绪
    exit /b 0
)

echo [INFO] 安装依赖（基础 + runtime + input + ui + win）...
python -m pip install -e "%PROJECT_DIR%[runtime,input,ui,win]" -q
if !errorlevel! neq 0 (
    echo [WARN] 完整依赖安装失败，尝试仅安装基础依赖...
    python -m pip install -e "%PROJECT_DIR%" -q
)
echo [OK] 依赖安装完成
exit /b 0

:error_exit
exit /b 1
