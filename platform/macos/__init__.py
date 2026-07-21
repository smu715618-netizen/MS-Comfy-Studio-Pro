# macOS 平台 GPU 后端 (预留)

支持 Apple Silicon Metal / MPS。

当前阶段仅为预留接口，后续待开发。

"""
from typing import Optional


def get_backend_name() -> str:
    """返回 macOS 平台的首选后端名称"""
    return "apple_metal"


def check_mps_available() -> bool:
    """检查 Apple Metal Performance Shaders 是否可用"""
    try:
        import torch
        return hasattr(torch, "mps") and torch.backends.mps.is_available()
    except ImportError:
        return False


def get_supported_backends() -> list:
    """返回 macOS 支持的后端列表"""
    backends = []
    try:
        import torch
        if hasattr(torch, "mps") and torch.backends.mps.is_available():
            backends.append("metal/mps")
    except ImportError:
        pass
    backends.append("cpu")
    return backends
