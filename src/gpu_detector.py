"""
GPU 检测模块

检测系统中可用的 GPU 设备，优先检测 Intel Arc XPU。
支持以下 GPU 类型：
- Intel Arc (DirectML / XPU)
- NVIDIA CUDA
- AMD ROCm
- CPU Only（无 GPU）
"""

import subprocess
import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from src.logger import get_logger

logger = get_logger("gpu")


class GPUType(Enum):
    """GPU 类型枚举"""
    INTEL_XPU = "intel_xpu"
    INTEL_DIRECTML = "intel_directml"
    NVIDIA_CUDA = "nvidia_cuda"
    AMD_ROCM = "amd_rocm"
    CPU_ONLY = "cpu_only"
    UNKNOWN = "unknown"


@dataclass
class GPUInfo:
    """GPU 信息数据结构"""
    gpu_type: GPUType = GPUType.UNKNOWN
    vendor: str = ""
    name: str = ""
    memory_total_mb: int = 0
    memory_used_mb: int = 0
    driver_version: str = ""
    compute_capability: str = ""
    directml_supported: bool = False
    xpu_supported: bool = False
    cuda_supported: bool = False
    rocm_supported: bool = False
    details: dict = field(default_factory=dict)


class GPUDetector:
    """
    GPU 检测器

    检测系统中所有可用的 GPU 设备，返回详细信息。
    优先检测 Intel Arc，其次是 NVIDIA CUDA，最后是 AMD ROCm。
    """

    def detect(self) -> GPUInfo:
        """
        检测系统中的 GPU

        Returns:
            GPUInfo 对象，包含检测到的 GPU 信息
        """
        info = GPUInfo()

        # 1. 检测 Intel Arc XPU / DirectML
        intel_info = self._detect_intel()
        if intel_info.name:
            info.gpu_type = GPUType.INTEL_XPU if intel_info.xpu_supported else GPUType.INTEL_DIRECTML
            info.vendor = intel_info.vendor
            info.name = intel_info.name
            info.memory_total_mb = intel_info.memory_total_mb
            info.driver_version = intel_info.driver_version
            info.directml_supported = intel_info.directml_supported
            info.xpu_supported = intel_info.xpu_supported
            info.details = intel_info.details
            logger.info(f"检测到 Intel GPU: {info.name}")
            return info

        # 2. 检测 NVIDIA CUDA
        nvidia_info = self._detect_nvidia()
        if nvidia_info.name:
            info.gpu_type = GPUType.NVIDIA_CUDA
            info.vendor = nvidia_info.vendor
            info.name = nvidia_info.name
            info.memory_total_mb = nvidia_info.memory_total_mb
            info.cuda_supported = True
            logger.info(f"检测到 NVIDIA GPU: {info.name}")
            return info

        # 3. 检测 AMD ROCm
        amd_info = self._detect_amd()
        if amd_info.name:
            info.gpu_type = GPUType.AMD_ROCM
            info.vendor = amd_info.vendor
            info.name = amd_info.name
            info.memory_total_mb = amd_info.memory_total_mb
            info.rocm_supported = True
            logger.info(f"检测到 AMD GPU: {info.name}")
            return info

        # 4. 默认 CPU Only
        logger.warning("未检测到 GPU，将使用 CPU 模式")
        info.gpu_type = GPUType.CPU_ONLY
        return info

    def _detect_intel(self) -> GPUInfo:
        """检测 Intel Arc GPU"""
        info = GPUInfo()
        info.vendor = "Intel Corporation"

        # 方法 1: 通过 Python 检测 torch
        try:
            import torch
            info.xpu_supported = hasattr(torch, "xpu") and torch.xpu.is_available()
            info.directml_supported = True  # DirectML 总是可用（Windows）

            if info.xpu_supported:
                info.name = "Intel Arc (XPU)"
                info.memory_total_mb = torch.xpu.get_device_properties(0).total_memory // (1024 * 1024)
                info.details = {"torch_version": torch.__version__, "xpu_available": True}
                return info

        except ImportError:
            pass  # PyTorch 未安装

        # 方法 2: 通过 DirectX 检测 DirectML
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-Table -HideTableHeaders"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if "intel" in output.lower():
                info.name = "Intel Arc (DirectML)"
                info.directml_supported = True
                # AdapterRAM 以字节为单位
                ram_str = output.split("\n")[-1].strip() if "\n" in output else ""
                if ram_str:
                    try:
                        info.memory_total_mb = int(ram_str) // (1024 * 1024)
                    except ValueError:
                        pass
                info.details = {"detection_method": "directx"}
                return info
        except Exception as e:
            logger.debug(f"DirectX 检测失败: {e}")

        # 方法 3: 通过 WMI 检测
        try:
            import wmi
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                if "intel" in gpu.Name.lower() or "arc" in gpu.Name.lower():
                    info.name = gpu.Name
                    if gpu.AdapterRAM:
                        info.memory_total_mb = gpu.AdapterRAM // (1024 * 1024)
                    info.driver_version = gpu.DriverVersion
                    info.directml_supported = True
                    info.details = {"detection_method": "wmi"}
                    return info
        except ImportError:
            pass  # wmi 模块未安装
        except Exception as e:
            logger.debug(f"WMI 检测失败: {e}")

        return info

    def _detect_nvidia(self) -> GPUInfo:
        """检测 NVIDIA GPU"""
        info = GPUInfo()
        info.vendor = "NVIDIA Corporation"

        try:
            import torch
            if torch.cuda.is_available():
                info.name = torch.cuda.get_device_name(0)
                info.memory_total_mb = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
                info.cuda_supported = True
                info.details = {"torch_version": torch.__version__, "cuda_available": True}
                return info
        except ImportError:
            pass

        # 通过 nvidia-smi 检测
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                line = result.stdout.strip().split("\n")[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    info.name = parts[0]
                    info.memory_total_mb = int(parts[1])
                    if len(parts) >= 3:
                        info.driver_version = parts[2]
                    info.cuda_supported = True
                    return info
        except (FileNotFoundError, ValueError) as e:
            logger.debug(f"NVIDIA 检测失败: {e}")

        return info

    def _detect_amd(self) -> GPUInfo:
        """检测 AMD GPU"""
        info = GPUInfo()
        info.vendor = "Advanced Micro Devices, Inc."

        try:
            result = subprocess.run(
                ["rocm-smi", "--showname", "--showmem-used", "--showmem-total"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines:
                    info.name = lines[0].strip()
                    info.rocm_supported = True
                    return info
        except FileNotFoundError:
            pass  # rocm-smi 不存在

        # 备用: 通过 DirectX 检测
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | Format-Table -HideTableHeaders"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if "amd" in output.lower() or "radeon" in output.lower():
                info.name = "AMD Radeon"
                info.rocm_supported = True
                return info
        except Exception:
            pass

        return info

    def get_recommended_backend(self) -> str:
        """
        根据检测到的 GPU 返回推荐的计算后端

        Returns:
            后端名称: "xpu", "cuda", "rocm", "directml", "cpu"
        """
        gpu_info = self.detect()
        if gpu_info.xpu_supported:
            return "xpu"
        elif gpu_info.cuda_supported:
            return "cuda"
        elif gpu_info.rocm_supported:
            return "rocm"
        elif gpu_info.directml_supported:
            return "directml"
        return "cpu"

    def check_compatibility(self) -> dict:
        """
        检查系统 GPU 兼容性

        Returns:
            兼容性检查结果
        """
        gpu = self.detect()
        result = {
            "compatible": False,
            "gpu_type": gpu.gpu_type.value,
            "gpu_name": gpu.name,
            "memory_mb": gpu.memory_total_mb,
            "recommendations": [],
        }

        # 检查最低显存要求 (4GB)
        if gpu.memory_total_mb < 4096:
            result["recommendations"].append(
                f"显存不足: 检测到 {gpu.memory_total_mb}MB，建议至少 4096MB"
            )
        elif gpu.memory_total_mb < 8192:
            result["recommendations"].append(
                f"显存较小: {gpu.memory_total_mb}MB，部分高级功能可能受限"
            )
        else:
            result["recommendations"].append("显存充足")

        # 检查 GPU 类型
        if gpu.gpu_type == GPUType.CPU_ONLY:
            result["recommendations"].append("未检测到 GPU，将使用 CPU 模式（速度较慢）")
        elif gpu.gpu_type == GPUType.INTEL_XPU:
            result["recommendations"].append("Intel Arc XPU 支持良好")
        elif gpu.gpu_type == GPUType.INTEL_DIRECTML:
            result["recommendations"].append("Intel Arc 将通过 DirectML 运行")
        elif gpu.gpu_type == GPUType.NVIDIA_CUDA:
            result["recommendations"].append("NVIDIA CUDA 支持良好")

        result["compatible"] = len(result["recommendations"]) == 0 or all(
            "不足" not in r for r in result["recommendations"]
        )

        return result
