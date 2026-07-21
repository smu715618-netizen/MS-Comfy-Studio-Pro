# platform 包 — 平台适配层

"""
跨平台 GPU 后端管理

按当前操作系统自动加载对应的 GPU 后端模块：
- Windows: Intel XPU / DirectML (NVIDIA CUDA 预留)
- macOS: Apple Metal (MPS)
- Linux: ROCm / CUDA / XPU

所有平台模块在启动时根据运行环境懒加载，
避免未使用的 GPU 后端占用内存空间。
"""

from enum import Enum


class Platform(Enum):
    """平台枚举"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


def get_platform() -> Platform:
    """
    检测当前运行平台

    Returns:
        Platform 枚举值
    """
    import sys
    if sys.platform == "win32":
        return Platform.WINDOWS
    elif sys.platform == "darwin":
        return Platform.MACOS
    elif sys.platform == "linux":
        return Platform.LINUX
    return Platform.UNKNOWN
