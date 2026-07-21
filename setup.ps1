# ============================================================
# MS Comfy Studio Pro - PowerShell 安装脚本
# ============================================================
# 功能：
# 1. 检测 Python 3.11+
# 2. 创建虚拟环境
# 3. 安装依赖
# 4. 克隆 ComfyUI
# 5. 安装 Intel XPU 依赖
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MS Comfy Studio Pro - PowerShell Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1 | Out-String
    Write-Host "  $pythonVersion.Trim()" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.11+" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "  Check 'Add Python to PATH' during installation." -ForegroundColor Gray
    Read-Host "Press Enter to exit"
    exit 1
}

# 验证版本 >= 3.11
$version = [System.Version]($pythonVersion.Trim().Replace("Python ", ""))
if ($version -lt [System.Version]"3.11") {
    Write-Host "[ERROR] Python version too old. Need >= 3.11" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  [OK] Python version is compatible" -ForegroundColor Green
Write-Host ""

# 创建虚拟环境
Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "  Virtual environment already exists, skipping." -ForegroundColor Gray
}
Write-Host "  [OK] Virtual environment ready" -ForegroundColor Green
Write-Host ""

# 激活虚拟环境并安装依赖
Write-Host "[3/5] Installing core dependencies..." -ForegroundColor Yellow
& venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] Some dependencies failed to install. Check network and retry." -ForegroundColor DarkYellow
}
Write-Host "  [OK] Core dependencies installed" -ForegroundColor Green
Write-Host ""

# 克隆 ComfyUI
Write-Host "[4/5] Cloning ComfyUI..." -ForegroundColor Yellow
if (-not (Test-Path "comfyui")) {
    git clone https://github.com/comfyanonymous/ComfyUI.git
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to clone ComfyUI" -ForegroundColor Red
        Write-Host "  Manual: git clone https://github.com/comfyanonymous/ComfyUI.git" -ForegroundColor Gray
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "  ComfyUI already exists, skipping." -ForegroundColor Gray
}
Write-Host "  [OK] ComfyUI ready" -ForegroundColor Green
Write-Host ""

# 安装 XPU 依赖
Write-Host "[5/5] Installing Intel XPU dependencies..." -ForegroundColor Yellow
pip install -r requirements-xpu.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] XPU dependencies may have issues" -ForegroundColor DarkYellow
}
Write-Host "  [OK] XPU dependencies installed" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Double-click run_launcher.bat to start the control panel" -ForegroundColor White
Write-Host "  2. Double-click run_comfy.bat to start ComfyUI" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close"
