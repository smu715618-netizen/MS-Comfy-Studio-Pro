"""start_config.py — 启动参数管理

根据硬件配置自动生成 ComfyUI 的启动参数。
支持低显存模式、模型卸载策略、内存优化等。

设计原则：
- 针对不同 GPU 型号自动选择最优参数
- 8GB VRAM 以下自动启用低显存模式
- 保留手动覆盖能力
- 不修改 ComfyUI 原始代码
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger
from src.config_manager import get_config
from src.gpu_detector import GPUDetector, GPUInfo, GPUType

logger = get_logger("start_config")


class VramMode(Enum):
    """显存管理模式"""
    LOW_VRAM = "low_vram"           # < 8GB
    NORMAL_VRAM = "normal_vram"     # 8-12GB
    HIGH_VRAM = "high_vram"         # > 12GB
    MAX_VRAM = "max_vram"           # > 16GB


@dataclass
class LaunchArgs:
    """ComfyUI 启动参数集合"""
    port: int = 8188
    host: str = "127.0.0.1"
    auto_open_browser: bool = False
    extra_args: List[str] = field(default_factory=list)
    vram_mode: VramMode = VramMode.NORMAL_VRAM
    max_batch_size: int = 1
    attention_slicing: bool = True
    vae_chunk_size: int = 4
    fp16_precision: bool = True
    low_cpu_mem_usage: bool = False

    def to_list(self) -> List[str]:
        """转换为命令行参数列表"""
        args = []

        if self.port != 8188:
            args.extend(["--port", str(self.port)])
        if self.host != "127.0.0.1":
            args.extend(["--host", self.host])
        if self.auto_open_browser:
            args.append("--auto-launch")

        # 显存管理
        if self.vram_mode == VramMode.LOW_VRAM:
            args.append("--low-vram")
        elif self.vram_mode == VramMode.HIGH_VRAM:
            args.append("--high-vram")
        elif self.vram_mode == VramMode.MAX_VRAM:
            args.append("--max-vram")

        # FP16 精度
        if self.fp16_precision:
            args.append("--fp16-vae")

        # Attention 切片
        if self.attention_slicing:
            args.append("--always-sliced-attention")

        return args

    def summary(self) -> Dict[str, Any]:
        """获取参数摘要（供 UI 显示）"""
        return {
            "port": self.port,
            "host": self.host,
            "vram_mode": self.vram_mode.value,
            "max_batch_size": self.max_batch_size,
            "attention_slicing": self.attention_slicing,
            "vae_chunk_size": self.vae_chunk_size,
            "fp16_precision": self.fp16_precision,
            "low_cpu_mem_usage": self.low_cpu_mem_usage,
            "all_args": " ".join(self.to_list()),
        }


class LaunchConfigManager:
    """
    启动配置管理器

    根据当前 GPU 信息自动推荐最优启动参数。
    用户也可手动调整设置。
    """

    # 预定义硬件配置文件
    _PRESETS = {
        "intel_arc_a750_8gb": {
            "vram_mode": VramMode.LOW_VRAM,
            "max_batch_size": 1,
            "attention_slicing": True,
            "vae_chunk_size": 4,
            "fp16_precision": True,
            "low_cpu_mem_usage": False,
        },
        "nvidia_rtx_3060_12gb": {
            "vram_mode": VramMode.NORMAL_VRAM,
            "max_batch_size": 1,
            "attention_slicing": True,
            "vae_chunk_size": 8,
            "fp16_precision": True,
            "low_cpu_mem_usage": False,
        },
        "nvidia_rtx_4090_24gb": {
            "vram_mode": VramMode.HIGH_VRAM,
            "max_batch_size": 2,
            "attention_slicing": False,
            "vae_chunk_size": 16,
            "fp16_precision": True,
            "low_cpu_mem_usage": True,
        },
        "cpu_only": {
            "vram_mode": VramMode.LOW_VRAM,
            "max_batch_size": 1,
            "attention_slicing": True,
            "vae_chunk_size": 2,
            "fp16_precision": False,
            "low_cpu_mem_usage": True,
        },
    }

    def __init__(self):
        self._config = get_config()
        self._gpu_info: Optional[GPUInfo] = None
        self._preset_name: str = ""
        self._custom_args: List[str] = []

    @property
    def gpu_info(self) -> Optional[GPUInfo]:
        """当前 GPU 信息"""
        return self._gpu_info

    def auto_detect(self) -> LaunchArgs:
        """
        自动检测硬件并生成推荐配置

        Returns:
            LaunchArgs 对象，包含推荐的所有启动参数
        """
        logger.info("正在检测硬件并生成启动配置...")

        # 检测 GPU
        detector = GPUDetector()
        self._gpu_info = detector.detect()

        # 选择预设
        preset_name = self._select_preset()

        # 从预设加载基础参数
        args = LaunchArgs()
        preset = self._PRESETS.get(preset_name, {})
        for key, value in preset.items():
            if hasattr(args, key):
                setattr(args, key, value)

        # 端口号从配置文件读取
        args.port = self._config.get("comfyui.port", 8188)
        args.host = self._config.get("comfyui.host", "127.0.0.1")
        args.auto_open_browser = self._config.get("comfyui.auto_open_browser", False)

        logger.info(f"已选择硬件预设: {preset_name}")
        logger.info(f"显存模式: {args.vram_mode.value}")
        logger.info(f"生成启动参数: {' '.join(args.to_list())}")

        return args

    def manual_config(
        self,
        port: int = 8188,
        vram_mode: Optional[VramMode] = None,
        extra_args: Optional[List[str]] = None,
    ) -> LaunchArgs:
        """
        手动指定配置

        Args:
            port: 监听端口
            vram_mode: 显存管理模式
            extra_args: 额外启动参数

        Returns:
            LaunchArgs 对象
        """
        args = LaunchArgs(port=port)

        if vram_mode:
            args.vram_mode = vram_mode

        if extra_args:
            args.extra_args = extra_args

        return args

    def set_custom_args(self, custom_args: List[str]):
        """设置自定义启动参数"""
        self._custom_args = custom_args

    def get_recommended_config(self) -> dict:
        """
        获取推荐配置摘要（供 UI 显示建议）

        Returns:
            配置摘要字典
        """
        if not self._gpu_info:
            detector = GPUDetector()
            self._gpu_info = detector.detect()

        preset = self._select_preset()
        base = self._PRESETS.get(preset, {})

        return {
            "recommended_preset": preset,
            "gpu_type": self._gpu_info.gpu_type.value,
            "memory_mb": self._gpu_info.memory_total_mb,
            "base_params": base,
            "custom_args_available": len(self._custom_args) > 0,
        }

    def _select_preset(self) -> str:
        """
        根据当前 GPU 信息选择最匹配的预设

        Returns:
            预设名称
        """
        if not self._gpu_info:
            return "cpu_only"

        gpu_type = self._gpu_info.gpu_type
        memory_mb = self._gpu_info.memory_total_mb

        # 无 GPU
        if gpu_type == GPUType.CPU_ONLY:
            return "cpu_only"

        # Intel Arc A750 8GB - 主要目标平台
        if gpu_type == GPUType.INTEL_XPU or gpu_type == GPUType.INTEL_DIRECTML:
            if memory_mb >= 8192:
                return "intel_arc_a750_8gb"
            elif memory_mb >= 4096:
                return "intel_arc_a750_8gb"  # 仍使用此预设，只是模式更激进
            return "cpu_only"

        # NVIDIA CUDA
        if gpu_type == GPUType.NVIDIA_CUDA:
            if memory_mb >= 20480:  # 20GB+
                return "nvidia_rtx_4090_24gb"
            elif memory_mb >= 12288:  # 12GB+
                return "nvidia_rtx_3060_12gb"
            return "nvidia_rtx_3060_12gb"

        # AMD ROCm
        if gpu_type == GPUType.AMD_ROCM:
            if memory_mb >= 20480:
                return "nvidia_rtx_4090_24gb"
            return "nvidia_rtx_3060_12gb"

        return "cpu_only"


# 全局单例
_launch_config_instance = None


def get_launch_config() -> LaunchConfigManager:
    """获取全局启动配置管理器（单例）"""
    global _launch_config_instance
    if _launch_config_instance is None:
        _launch_config_instance = LaunchConfigManager()
    return _launch_config_instance


if __name__ == "__main__":
    # 命令行工具：查看推荐的启动配置
    print("=" * 50)
    print("  MS Comfy Studio Pro - Launch Config")
    print("=" * 50)
    print()

    mgr = LaunchConfigManager()
    args = mgr.auto_detect()

    print(f"GPU Type:   {mgr.gpu_info.gpu_type.value if mgr.gpu_info else 'Unknown'}")
    print(f"GPU Name:   {mgr.gpu_info.name if mgr.gpu_info else 'N/A'}")
    print(f"VRAM:       {mgr.gpu_info.memory_total_mb if mgr.gpu_info else 'N/A'}MB")
    print(f"VRAM Mode:  {args.vram_mode.value}")
    print(f"Port:       {args.port}")
    print(f"Host:       {args.host}")
    print()
    print(f"Full command: python main.py {' '.join(args.to_list())}")
