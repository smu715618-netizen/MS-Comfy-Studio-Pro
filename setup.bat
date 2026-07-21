@echo off
REM ============================================================
REM MS Comfy Studio Pro - 安装脚本 (Windows)
REM ============================================================
REM 功能：
REM 1. 检测 Python 3.11+
REM 2. 创建虚拟环境
REM 3. 安装依赖
REM 4. 克隆 ComfyUI
REM 5. 安装 Intel XPU 依赖
REM ============================================================

setlocal EnableDelayedExpansion

echo ========================================
echo   MS Comfy Studio Pro - 安装向导
echo ========================================
echo.

REM 检查 Python
echo [1/5] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python 版本: !PYTHON_VERSION!

REM 检查版本 >= 3.11
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if !MAJOR!.lss 3 (
    echo [错误] Python 版本过低，需要 >= 3.11
    pause
    exit /b 1
)
if !MAJOR!.eq 3 if !MINOR!.lss 11 (
    echo [错误] Python 版本过低，需要 >= 3.11
    pause
    exit /b 1
)

echo [OK] Python 版本符合要求
echo.

REM 创建虚拟环境
echo [2/5] 创建虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)
echo [OK] 虚拟环境创建成功
echo.

REM 激活虚拟环境并安装依赖
echo [3/5] 安装核心依赖...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，请检查网络后重试
)
echo [OK] 核心依赖安装完成
echo.

REM 克隆 ComfyUI
echo [4/5] 克隆 ComfyUI...
if not exist comfyui (
    git clone https://github.com/comfyanonymous/ComfyUI.git
    if %errorlevel% neq 0 (
        echo [错误] 克隆 ComfyUI 失败
        echo 请手动克隆: git clone https://github.com/comfyanonymous/ComfyUI.git
        pause
        exit /b 1
    )
)
echo [OK] ComfyUI 准备就绪
echo.

REM 安装 XPU 依赖
echo [5/5] 安装 Intel XPU 依赖...
pip install -r requirements-xpu.txt
if %errorlevel% neq 0 (
    echo [警告] XPU 依赖安装可能有问题
)
echo [OK] XPU 依赖安装完成
echo.

echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 下一步：
echo   1. 双击 run_launcher.bat 启动管理面板
echo   2. 双击 run_comfy.bat 启动 ComfyUI
echo.
pause
