# Linux 平台 GPU 后端 (预留)

支持：
- NVIDIA CUDA
- AMD ROCm
- Intel XPU

当前阶段仅为预留接口，后续待开发。

"""
from typing import Optional


def get_backend_name() -> str:
    """返回 Linux 平台的首选后端名称"""
    return "cuda"


def check_cuda_available() -> bool:
    """检查 NVIDIA CUDA 是否可用"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def check_rocm_available() -> bool:
    """检查 AMD ROCm 是否可用"""
    try:
        import torch
        return hasattr(torch, "cuda") and hasattr(torch.cuda, "is_available")
    except ImportError:
        return False


def get_supported_backends() -> list:
    """返回 Linux 支持的后端列表"""
    backends = ["cpu"]
    try:
        import torch
        if torch.cuda.is_available():
            backends.insert(0, "cuda")
    except ImportError:
        pass
    return backends
