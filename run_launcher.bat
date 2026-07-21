@echo off
REM ============================================================
REM MS Comfy Studio Pro - 启动管理面板
REM ============================================================
REM 功能：
REM 1. 检查环境是否已安装
REM 2. 激活虚拟环境
REM 3. 启动 PyQt6 管理面板
REM ============================================================

setlocal

echo ========================================
echo   MS Comfy Studio Pro - 管理面板
echo ========================================
echo.

REM 检查虚拟环境
if not exist venv\Scripts\python.exe (
    echo [错误] 虚拟环境不存在，请先运行 setup.bat
    pause
    exit /b 1
)

echo 正在启动管理面板...
echo.

REM 启动 GUI 应用
venv\Scripts\python.exe -m src.gui.app

pause
