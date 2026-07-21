@echo off
REM ============================================================
REM MS Comfy Studio Pro - 卸载脚本
REM ============================================================
REM 功能：
REM 1. 停止正在运行的 ComfyUI 进程
REM 2. 删除虚拟环境
REM 3. 删除 ComfyUI 目录
REM 4. 删除数据目录（可选）
REM ============================================================

setlocal

echo ========================================
echo   MS Comfy Studio Pro - 卸载向导
echo ========================================
echo.

echo [警告] 此操作将删除虚拟环境和 ComfyUI，但会保留您的模型和工作流。
echo.

REM 检查是否有运行中的 ComfyUI
tasklist /fi "IMAGENAME eq python.exe" | findstr python >nul
if %errorlevel% equ 0 (
    echo [警告] 检测到 Python 进程正在运行
    echo 请先手动停止 ComfyUI
    pause
    exit /b 1
)

echo [1/3] 删除虚拟环境...
if exist venv (
    rmdir /s /q venv
    echo [OK] 虚拟环境已删除
) else (
    echo [跳过] 虚拟环境不存在
)
echo.

echo [2/3] 删除 ComfyUI...
if exist comfyui (
    rmdir /s /q comfyui
    echo [OK] ComfyUI 已删除
) else (
    echo [跳过] ComfyUI 不存在
)
echo.

echo [3/3] 清理临时文件...
if exist __pycache__ rmdir /s /q __pycache__
if exist src\__pycache__ rmdir /s /q src\__pycache__
echo [OK] 临时文件已清理
echo.

echo ========================================
echo   卸载完成！
echo ========================================
echo.
echo 提示：如需完全卸载，请手动删除以下目录：
echo   - data/models (模型文件)
echo   - data/workflows/user (用户工作流)
echo   - configs/local.yaml (本地配置)
echo.
pause
