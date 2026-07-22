# macOS GPU 后端模块 (预留)

"""
macOS平台GPU管理 — 预留接口

支持的后端：
1. Apple Metal / MPS (PyTorch MPS后端)
2. CPU (兜底)

**设计原则：**
- 此模块仅在macOS平台加载
- PyTorch MPS后端与CUDA接口类似，迁移成本低
- 统一内存架构简化显存管理

**何时启用：** 收到明确macOS用户需求时
"""

import sys


def get_backend_type() -> str:
    """返回当前平台的GPU后端类型标识"""
    return "macos"


def check_mps_available() -> bool:
    """
    检查Apple Metal Performance Shaders是否可用

    Returns:
        True if torch.backends.mps.is_available()
    """
    try:
        import torch
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        return False


def generate_launch_args(vram_mode: str = "normal_vram") -> list:
    """
    为macOS生成ComfyUI启动参数

    Args:
        vram_mode: VRAM管理模式

    Returns:
        命令行参数列表
    """
    args = []

    if vram_mode == "low_vram":
        args.extend(["--low-vram"])
    elif vram_mode == "normal_vram":
        args.extend(["--normal-vram"])

    # Metal会自动处理GPU加速，无需额外标志
    return args


def get_compatible_backends() -> list:
    """
    获取当前macOS系统兼容的GPU后端列表

    Returns:
        ['metal'] or ['cpu']
    """
    if check_mps_available():
        return ["metal"]
    return ["cpu"]


if __name__ == "__main__":
    print(f"Backend type: {get_backend_type()}")
    print(f"MPS available: {check_mps_available()}")
    print(f"Compatible backends: {get_compatible_backends()}")
