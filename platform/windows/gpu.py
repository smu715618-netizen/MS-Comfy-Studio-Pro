# Windows GPU 后端模块

"""
Windows平台GPU管理

支持的后端（按优先级）：
1. Intel XPU — PyTorch XPU后端，性能最优
2. DirectML — DirectX 12抽象层，兼容性兜底
3. NVIDIA CUDA (预留) — 未来扩展

**关键设计原则：**
- 此模块仅在Windows平台加载
- 默认不会同时加载所有GPU后端
- 运行时根据检测到的硬件自动选择
- 未使用的GPU驱动不进入内存空间
"""

import sys
import subprocess
from typing import Optional, Dict, Any


def get_backend_type() -> str:
    """返回当前Windows平台的GPU后端类型标识"""
    return "windows"


def check_xpu_available() -> bool:
    """
    检查Intel XPU是否可用

    Returns:
        True if torch.xpu.is_available(), else False
    """
    try:
        import torch
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            return True
    except ImportError:
        pass
    return False


def check_directml_available() -> bool:
    """
    检查DirectML是否可用（Windows上几乎总是可用）

    Returns:
        True 如果DirectML可用
    """
    # DirectML在Windows上始终可用（通过D3D12抽象层）
    return True


def detect_gpu_via_powershell() -> dict:
    """
    通过PowerShell获取Windows GPU信息

    Returns:
        {name, memory_mb, driver_version} 字典
    """
    result = {}
    try:
        ps_cmd = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, AdapterRAM, DriverVersion | "
            "Format-List | Out-String"
        )
        output = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()

        for line in output.split('\n'):
            parts = line.split(':', 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                if 'Name' in key or 'name' in key.lower():
                    result['name'] = value
                elif 'AdapterRAM' in key:
                    try:
                        result['memory_mb'] = int(value) // (1024 * 1024)
                    except:
                        pass
                elif 'DriverVersion' in key:
                    result['driver_version'] = value

    except Exception as e:
        result['_error'] = str(e)

    if not result.get('name'):
        result['name'] = 'Unknown GPU'
        result['memory_mb'] = 0

    return result


def generate_launch_args(vram_mode: str = "low_vram") -> list:
    """
    为Windows生成ComfyUI启动参数

    Args:
        vram_mode: VRAM管理模式 ('low_vram', 'normal_vram', 'high_vram')

    Returns:
        命令行参数列表
    """
    args = []

    if vram_mode == "low_vram":
        args.extend(["--low-vram"])
    elif vram_mode == "normal_vram":
        args.extend(["--normal-vram"])
    elif vram_mode == "high_vram":
        args.extend(["--high-vram"])

    # 检测XPU优先
    if check_xpu_available():
        args.append("--xpu")
    else:
        args.append("--directml")

    return args


def get_compatible_backends() -> list:
    """
    获取当前Windows系统兼容的GPU后端列表

    Returns:
        ['xpu'], ['xpu', 'directml'], 或 ['directml']
    """
    backends = []

    if check_xpu_available():
        backends.append("xpu")

    if check_directml_available():
        backends.append("directml")

    # NVIDIA CUDA预留
    # if torch.cuda.is_available():
    #     backends.append("cuda")

    return backends if backends else ["cpu_only"]
