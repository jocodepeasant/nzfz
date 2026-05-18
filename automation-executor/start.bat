@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_DIR=%SCRIPT_DIR%"
set "VENV_DIR=%PROJECT_DIR%\.venv"

set "PYTHON="

echo ═════════════════════════════════════
echo   TD Executor - 塔防自动化执行器
echo ═════════════════════════════════════
echo.

call :check_python
if errorlevel 1 goto :error_exit

call :setup_venv
if errorlevel 1 goto :error_exit

call :activate_venv
if errorlevel 1 goto :error_exit

call :install_deps
if errorlevel 1 goto :error_exit

echo.

set "CMD=%~1"
if "%CMD%"=="" set "CMD=help"

if "%CMD%"=="gui" goto :run_gui
if "%CMD%"=="run" goto :run_script
if "%CMD%"=="validate" goto :run_validate
if "%CMD%"=="dry-run" goto :run_dry_run
if "%CMD%"=="test" goto :run_tests
if "%CMD%"=="help" goto :show_help
if "%CMD%"=="--help" goto :show_help
if "%CMD%"=="-h" goto :show_help

echo [ERROR] 未知命令: %CMD%
echo.
goto :show_help

:run_gui
echo [INFO] 启动 GUI 界面...
if not exist "%PROJECT_DIR%\reports" mkdir "%PROJECT_DIR%\reports"
"%PYTHON%" -m td_executor gui
goto :eof

:run_script
set "SCRIPT_PATH=%~2"
if "%SCRIPT_PATH%"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 run ^<脚本路径^>
    goto :error_exit
)
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] 脚本文件不存在: %SCRIPT_PATH%
    goto :error_exit
)
echo [INFO] 执行脚本: %SCRIPT_PATH%
if not exist "%PROJECT_DIR%\reports" mkdir "%PROJECT_DIR%\reports"
"%PYTHON%" -m td_executor run "%SCRIPT_PATH%"
goto :eof

:run_validate
set "SCRIPT_PATH=%~2"
if "%SCRIPT_PATH%"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 validate ^<脚本路径^>
    goto :error_exit
)
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] 脚本文件不存在: %SCRIPT_PATH%
    goto :error_exit
)
"%PYTHON%" -m td_executor validate "%SCRIPT_PATH%"
goto :eof

:run_dry_run
set "SCRIPT_PATH=%~2"
if "%SCRIPT_PATH%"=="" (
    echo [ERROR] 请指定脚本文件路径
    echo 用法: %~nx0 dry-run ^<脚本路径^>
    goto :error_exit
)
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] 脚本文件不存在: %SCRIPT_PATH%
    goto :error_exit
)
echo [INFO] 试运行: %SCRIPT_PATH%
"%PYTHON%" -m td_executor run "%SCRIPT_PATH%" --dry-run
goto :eof

:run_tests
echo [INFO] 运行测试...
"%PYTHON%" -m pytest "%PROJECT_DIR%\tests" -v
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
if %errorlevel%==0 (
    set "PYTHON=python"
    goto :check_version
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python3"
    goto :check_version
)
echo [ERROR] 未找到 Python，请安装 Python ^>= 3.10
exit /b 1

:check_version
for /f "tokens=*" %%v in ('"%PYTHON%" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VERSION=%%v"
for /f "tokens=1 delims=." %%m in ("%PY_VERSION%") do set "PY_MAJOR=%%m"
for /f "tokens=2 delims=." %%n in ("%PY_VERSION%") do set "PY_MINOR=%%n"

if %PY_MAJOR% lss 3 (
    echo [ERROR] Python 版本过低 ^(%PY_VERSION%^)，需要 ^>= 3.10
    exit /b 1
)
if %PY_MAJOR%==3 if %PY_MINOR% lss 10 (
    echo [ERROR] Python 版本过低 ^(%PY_VERSION%^)，需要 ^>= 3.10
    exit /b 1
)
echo [OK] Python %PY_VERSION%
exit /b 0

:setup_venv
if not exist "%VENV_DIR%" (
    echo [INFO] 创建虚拟环境...
    "%PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败
        exit /b 1
    )
    echo [OK] 虚拟环境已创建: %VENV_DIR%
)
exit /b 0

:activate_venv
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
    echo [OK] 虚拟环境已激活
    exit /b 0
)
echo [ERROR] 虚拟环境激活失败，请检查 %VENV_DIR%
exit /b 1

:install_deps
set "PKGS_INSTALLED=0"

"%PYTHON%" -c "import td_executor" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 td-executor（基础依赖）...
    "%PYTHON%" -m pip install -e "%PROJECT_DIR%" -q
    set "PKGS_INSTALLED=1"
)

"%PYTHON%" -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 runtime 依赖（numpy, opencv, mss）...
    "%PYTHON%" -m pip install -e "%PROJECT_DIR%\[runtime\]" -q
    set "PKGS_INSTALLED=1"
)

"%PYTHON%" -c "import pynput" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 input 依赖（pynput, pyautogui）...
    "%PYTHON%" -m pip install -e "%PROJECT_DIR%\[input\]" -q
    set "PKGS_INSTALLED=1"
)

"%PYTHON%" -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 ui 依赖（Pillow）...
    "%PYTHON%" -m pip install -e "%PROJECT_DIR%\[ui\]" -q
    set "PKGS_INSTALLED=1"
)

if "%PKGS_INSTALLED%"=="1" (
    echo [OK] 依赖安装完成
) else (
    echo [OK] 所有依赖已就绪
)
exit /b 0

:error_exit
exit /b 1
