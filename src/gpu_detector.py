"""GPU 检测模块

检测系统中可用的 GPU 设备，以 Intel Arc XPU 为主要路线，DirectML 为备用路线。
支持以下 GPU 类型（按优先级）：
- Intel Arc (XPU / DirectML)
- NVIDIA CUDA
- AMD ROCm
- CPU Only（无 GPU）

同时提供完整的系统信息检测（CPU、内存、Python环境）。
"""

import subprocess
import sys
import os
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from src.logger import get_logger
from src.config_manager import get_config

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
class SystemInfo:
    """系统信息"""
    cpu_name: str = ""
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    total_memory_mb: int = 0
    available_memory_mb: int = 0
    python_version: str = ""
    python_64bit: bool = False
    os_name: str = ""
    os_version: str = ""

    def to_dict(self) -> dict:
        return {
            "cpu_name": self.cpu_name,
            "cpu_cores_physical": self.cpu_cores_physical,
            "cpu_cores_logical": self.cpu_cores_logical,
            "total_memory_mb": self.total_memory_mb,
            "available_memory_mb": self.available_memory_mb,
            "python_version": self.python_version,
            "python_64bit": self.python_64bit,
            "os_name": self.os_name,
            "os_version": self.os_version,
        }


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

    def to_dict(self) -> dict:
        return {
            "gpu_type": self.gpu_type.value,
            "vendor": self.vendor,
            "name": self.name,
            "memory_total_mb": self.memory_total_mb,
            "memory_used_mb": self.memory_used_mb,
            "driver_version": self.driver_version,
            "compute_capability": self.compute_capability,
            "directml_supported": self.directml_supported,
            "xpu_supported": self.xpu_supported,
            "cuda_supported": self.cuda_supported,
            "rocm_supported": self.rocm_supported,
            "details": self.details,
        }


class GPUDetector:
    """
    GPU 检测器

    检测系统中所有可用的 GPU 设备，返回详细信息。
    检测优先级（按路线）：
    1. Intel Arc XPU (主路线)
    2. Intel Arc DirectML (备用路线)
    3. NVIDIA CUDA
    4. AMD ROCm
    5. CPU Only
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
        """
        检测 Intel Arc GPU

        优先级:
        1. Intel XPU (主路线) - 使用 PyTorch XPU 后端，性能最优
        2. DirectML (备用路线) - 使用 DirectX 12 抽象层，兼容性好
        """
        info = GPUInfo()
        info.vendor = "Intel Corporation"

        # 优先级 1: 检测 Intel XPU (主路线)
        try:
            import torch
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                info.xpu_supported = True
                info.name = "Intel Arc (XPU)"
                info.memory_total_mb = torch.xpu.get_device_properties(0).total_memory // (1024 * 1024)
                info.details = {"torch_version": torch.__version__, "xpu_available": True}
                logger.info(f"检测到 Intel Arc XPU (主路线): {info.name}")
                return info
        except ImportError:
            pass  # PyTorch 未安装，跳过 XPU 检测

        # 优先级 2: 检测 DirectML (备用路线)
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-Table -HideTableHeaders"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if "intel" in output.lower():
                info.directml_supported = True
                info.name = "Intel Arc (DirectML)"
                # AdapterRAM 以字节为单位
                ram_str = output.split("\n")[-1].strip() if "\n" in output else ""
                if ram_str:
                    try:
                        info.memory_total_mb = int(ram_str) // (1024 * 1024)
                    except ValueError:
                        pass
                info.details = {"detection_method": "directx", "fallback_from_xpu": True}
                logger.info(f"检测到 Intel Arc DirectML (备用路线): {info.name}")
                return info
        except Exception as e:
            logger.debug(f"DirectX 检测失败: {e}")

        # 备用: 通过 WMI 检测
        try:
            import wmi
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                if "intel" in gpu.Name.lower() or "arc" in gpu.Name.lower():
                    info.directml_supported = True
                    info.name = gpu.Name
                    if gpu.AdapterRAM:
                        info.memory_total_mb = gpu.AdapterRAM // (1024 * 1024)
                    info.driver_version = gpu.DriverVersion
                    info.details = {"detection_method": "wmi", "fallback_from_xpu": True}
                    logger.info(f"检测到 Intel Arc (备用路线): {info.name}")
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

    def get_system_info(self) -> SystemInfo:
        """
        获取完整的系统信息（CPU + 内存 + Python 环境）

        Returns:
            SystemInfo 对象
        """
        info = SystemInfo()

        # CPU 信息
        info.cpu_cores_logical = os.cpu_count() or 1

        # Windows: 尝试获取物理核心数
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors"],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) >= 2:
                    info.cpu_name = lines[1].split(',')[0].strip()
                    for part in lines[1].split(','):
                        part = part.strip()
                        if 'Core' in part:
                            info.cpu_cores_physical = int(part.replace('Core', '').replace('s', '').strip())
            except Exception:
                info.cpu_name = platform.processor() or "Unknown"

        if not info.cpu_name:
            info.cpu_name = platform.processor() or "Unknown CPU"

        # 内存信息
        try:
            import psutil
            vm = psutil.virtual_memory()
            info.total_memory_mb = vm.total // (1024 * 1024)
            info.available_memory_mb = vm.available // (1024 * 1024)
        except ImportError:
            info.total_memory_mb = 16384  # 假设 16GB
            info.available_memory_mb = 8192

        # Python 环境
        info.python_version = platform.python_version()
        info.python_64bit = sys.maxsize > 2**32

        # OS 信息
        info.os_name = platform.system()
        info.os_version = platform.version()

        return info

    def get_full_hardware_report(self) -> Dict[str, Any]:
        """
        获取完整的硬件报告

        Returns:
            包含 GPU、CPU、内存等完整信息的字典
        """
        gpu = self.detect()
        sys_info = self.get_system_info()
        compat = self.check_compatibility()

        return {
            "gpu": gpu.to_dict(),
            "system": sys_info.to_dict(),
            "compatibility": compat,
            "recommended_backend": self.get_recommended_backend(),
        }
