# platform/windows 包

"""
Windows 平台 GPU 后端

支持：
- Intel XPU (主路线) — PyTorch XPU 后端
- DirectML (备用路线) — Windows DirectX 12 抽象层
- NVIDIA CUDA (预留) — 未来扩展
"""

from typing import Optional


def get_backend_name() -> str:
    """返回当前 Windows 平台的首选后端名称"""
    return "intel_xpu"


def check_xpu_available() -> bool:
    """检查 Intel XPU 是否可用"""
    try:
        import torch
        return hasattr(torch, "xpu") and torch.xpu.is_available()
    except ImportError:
        return False


def check_directml_available() -> bool:
    """检查 DirectML 是否可用"""
    try:
        import torch
        # DirectML 在 Windows 上通常可用
        return True
    except ImportError:
        return False
