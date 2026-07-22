"""cpu_monitor.py — CPU和内存监控系统

监控当前系统的CPU使用率和内存使用情况。
针对 Intel Arc A750 8GB + 16GB RAM 配置进行了优化。
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger
from src.config_manager import ConfigManager

logger = get_logger("monitor")


@dataclass
class CpuInfo:
    """CPU信息"""
    name: str = ""
    vendor: str = ""
    physical_cores: int = 0
    logical_cores: int = 0
    max_clock_mhz: int = 0
    current_load_percent: float = 0.0


@dataclass
class MemoryInfo:
    """内存信息"""
    total_mb: int = 0
    used_mb: int = 0
    available_mb: int = 0
    swap_total_mb: int = 0
    swap_used_mb: int = 0
    usage_percent: float = 0.0


@dataclass
class SystemHealth:
    """系统健康状态综合数据"""
    cpu: CpuInfo = field(default_factory=CpuInfo)
    memory: MemoryInfo = field(default_factory=MemoryInfo)
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    timestamp: str = ""


class CpuMonitor:
    """CPU使用率监控"""

    @staticmethod
    def detect() -> CpuInfo:
        """检测当前CPU信息"""
        info = CpuInfo()
        system = platform.system()

        try:
            if system == "Windows":
                info = CpuMonitor._detect_windows()
            elif system == "Linux":
                info = CpuMonitor._detect_linux()
            else:
                info.name = platform.processor() or "Unknown"
                info.logical_cores = os.cpu_count() or 1
        except Exception as e:
            logger.warning(f"CPU检测失败: {e}")

        # 获取最近一次CPU负载
        info.current_load_percent = CpuMonitor.get_current_load()
        return info

    @staticmethod
    def _detect_windows() -> CpuInfo:
        """Windows平台CPU检测"""
        info = CpuInfo()

        # 获取CPU信息
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name,NumberOfCores,MaxClockSpeed"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
            if len(lines) >= 2:
                info.name = lines[1].split(',')[0].strip()
                if not info.name:
                    info.name = "Unknown CPU"
        except Exception:
            info.name = platform.processor() or "Unknown"

        info.logical_cores = os.cpu_count() or 1
        return info

    @staticmethod
    def _detect_linux() -> CpuInfo:
        """Linux平台CPU检测"""
        import psutil
        info = CpuInfo()

        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        info.name = line.split(':')[1].strip()
                        break
        except Exception:
            info.name = platform.processor() or "Unknown CPU"

        info.logical_cores = os.cpu_count() or 1
        return info

    @staticmethod
    def get_current_load(interval: float = 1.0) -> float:
        """获取当前CPU使用率百分比"""
        try:
            import psutil
            load = psutil.cpu_percent(interval=interval)
            return float(load)
        except ImportError:
            return 0.0


class MemoryMonitor:
    """内存使用监控"""

    @staticmethod
    def detect() -> MemoryInfo:
        """检测当前内存使用情况"""
        info = MemoryInfo()
        system = platform.system()

        try:
            if system == "Windows":
                info = MemoryMonitor._detect_windows()
            elif system == "Linux":
                info = MemoryMonitor._detect_linux()
            else:
                info.total_mb = 16384  # 默认16GB
        except Exception as e:
            logger.warning(f"内存检测失败: {e}")

        return info

    @staticmethod
    def _detect_windows() -> MemoryInfo:
        """Windows平台内存检测"""
        import psutil
        info = MemoryInfo()

        vm = psutil.virtual_memory()
        info.total_mb = vm.total // (1024 * 1024)
        info.used_mb = vm.used // (1024 * 1024)
        info.available_mb = vm.available // (1024 * 1024)
        info.usage_percent = vm.percent

        # Swap page file
        try:
            swap = psutil.swap_memory()
            info.swap_total_mb = swap.total // (1024 * 1024)
            info.swap_used_mb = swap.used // (1024 * 1024)
        except Exception:
            pass

        return info

    @staticmethod
    def _detect_linux() -> MemoryInfo:
        """Linux平台内存检测"""
        import psutil
        info = MemoryInfo()

        vm = psutil.virtual_memory()
        info.total_mb = vm.total // (1024 * 1024)
        info.used_mb = vm.used // (1024 * 1024)
        info.available_mb = vm.available // (1024 * 1024)
        info.usage_percent = vm.percent

        try:
            swap = psutil.swap_memory()
            info.swap_total_mb = swap.total // (1024 * 1024)
            info.swap_used_mb = swap.used // (1024 * 1024)
        except Exception:
            pass

        return info


def get_system_health() -> SystemHealth:
    """
    获取完整的系统健康状态

    Returns:
        SystemHealth对象，包含CPU、内存、OS等综合信息
    """
    health = SystemHealth()

    # 检测CPU
    health.cpu = CpuMonitor.detect()

    # 检测内存
    health.memory = MemoryMonitor.detect()

    # 系统信息
    health.os_name = platform.system()
    health.os_version = platform.version()
    health.python_version = platform.python_version()

    from datetime import datetime
    health.timestamp = datetime.now().isoformat()

    return health


def check_minimum_requirements(health: SystemHealth) -> tuple:
    """
    检查系统是否满足最低运行要求

    Args:
        health: 系统健康状态

    Returns:
        (是否通过, 警告列表)
    """
    warnings = []

    # 检查Python版本
    try:
        parts = health.python_version.split('.')
        major, minor = int(parts[0]), int(parts[1])
        if major < 3 or (major == 3 and minor < 11):
            warnings.append(f"Python版本过低: {health.python_version}，需要>=3.11")
    except Exception:
        warnings.append("无法确定Python版本")

    # 检查内存
    total_mb = health.memory.total_mb
    if total_mb < 12288:  # 12GB
        warnings.append(f"内存不足: {total_mb}MB，建议>=16GB")
    elif total_mb < 16384:  # 16GB
        warnings.append(f"内存较小: {total_mb}MB，建议>=16GB")

    # 检查CPU核心数
    if health.cpu.logical_cores < 4:
        warnings.append(f"CPU核心数过少: {health.cpu.logical_cores}，建议>=4核")

    return len(warnings) == 0, warnings


if __name__ == "__main__":
    # 命令行工具：查看系统健康状态
    print("=" * 50)
    print("  MS Comfy Studio Pro - System Health Check")
    print("=" * 50)
    print()

    health = get_system_health()
    cpu = health.cpu
    mem = health.memory

    print(f"CPU:  {cpu.name}")
    print(f"      Cores: {cpu.physical_cores}P / {cpu.logical_cores}L")
    print(f"      Load:   {cpu.current_load_percent:.1f}%")
    print()
    print(f"Memory: Total    {mem.total_mb}MB")
    print(f"        Used     {mem.used_mb}MB ({mem.usage_percent:.1f}%)")
    print(f"        Available{mem.available_mb}MB")
    print()
    print(f"System: OS    {health.os_name} {health.os_version}")
    print(f"        Python {health.python_version}")
    print()

    passed, warnings = check_minimum_requirements(health)
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("All minimum requirements met.")
