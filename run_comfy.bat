@echo off
REM ============================================================
REM MS Comfy Studio Pro - 启动 ComfyUI
REM ============================================================
REM 功能：
REM 1. 检查环境是否已安装
REM 2. 激活虚拟环境
REM 3. 启动 ComfyUI 服务
REM ============================================================

setlocal

echo ========================================
echo   启动 ComfyUI
echo ========================================
echo.

REM 检查虚拟环境
if not exist venv\Scripts\python.exe (
    echo [错误] 虚拟环境不存在，请先运行 setup.bat
    pause
    exit /b 1
)

REM 检查 ComfyUI
if not exist comfyui\main.py (
    echo [错误] ComfyUI 不存在，请先运行 setup.bat
    pause
    exit /b 1
)

echo 正在启动 ComfyUI...
echo 服务地址: http://127.0.0.1:8188
echo.

REM 启动 ComfyUI（使用虚拟环境的 Python）
venv\Scripts\python.exe comfyui\main.py --port 8188

pause
