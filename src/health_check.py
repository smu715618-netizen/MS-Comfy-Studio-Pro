"""
健康检查模块

定期检查系统各项指标：
- GPU 状态和显存使用
- Python 版本
- 磁盘空间
- 网络连接
- 模型完整性
- 依赖完整性
- ComfyUI 服务状态
"""

import os
import platform
import socket
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from src.logger import get_logger
from src.gpu_detector import GPUDetector, GPUInfo

logger = get_logger("health")


class CheckStatus(Enum):
    """检查状态"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    """单个检查结果"""
    name: str
    status: CheckStatus
    message: str
    details: dict = field(default_factory=dict)


class HealthChecker:
    """
    健康检查器

    运行一系列检查，返回系统健康状态报告。
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化健康检查器

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            project_root = str(Path(__file__).parent.parent)
        self._project_root = Path(project_root)

    def run_all(self) -> Dict[str, dict]:
        """
        运行所有健康检查

        Returns:
            {检查名称: 检查结果字典}
        """
        checks = {
            "gpu": self.check_gpu,
            "python": self.check_python,
            "disk_space": self.check_disk_space,
            "network": self.check_network,
            "dependencies": self.check_dependencies,
            "comfyui": self.check_comfyui,
            "data_dirs": self.check_data_dirs,
        }

        results = {}
        for name, check_fn in checks.items():
            try:
                result = check_fn()
                results[name] = result
            except Exception as e:
                results[name] = {
                    "status": "fail",
                    "message": f"检查异常: {e}",
                }
                logger.error(f"{name} 检查异常: {e}")

        return results

    def check_gpu(self) -> dict:
        """检查 GPU 状态"""
        detector = GPUDetector()
        gpu_info = detector.detect()

        result = {
            "status": "pass",
            "message": f"GPU: {gpu_info.name} ({gpu_info.gpu_type.value})",
            "details": {
                "type": gpu_info.gpu_type.value,
                "name": gpu_info.name,
                "vendor": gpu_info.vendor,
                "memory_total_mb": gpu_info.memory_total_mb,
                "xpu_supported": gpu_info.xpu_supported,
                "directml_supported": gpu_info.directml_supported,
            },
        }

        # 检查显存是否足够
        if gpu_info.memory_total_mb < 4096:
            result["status"] = "fail"
            result["message"] = f"显存不足: {gpu_info.memory_total_mb}MB"
        elif gpu_info.memory_total_mb < 8192:
            result["status"] = "warn"
            result["message"] = f"显存较小: {gpu_info.memory_total_mb}MB"

        return result

    def check_python(self) -> dict:
        """检查 Python 版本"""
        result = {
            "status": "pass",
            "message": "",
            "details": {},
        }

        version = platform.python_version()
        result["details"]["version"] = version
        result["message"] = f"Python {version}"

        # 检查最低版本
        parts = version.split(".")
        major, minor = int(parts[0]), int(parts[1])
        if major < 3 or (major == 3 and minor < 11):
            result["status"] = "fail"
            result["message"] = f"Python 版本过低: {version}，需要 >= 3.11"

        return result

    def check_disk_space(self) -> dict:
        """检查磁盘空间"""
        result = {
            "status": "pass",
            "message": "",
            "details": {},
        }

        # 检查项目所在驱动器
        drive = self._project_root.drive or "/"
        try:
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_percent = (usage.used / usage.total) * 100

            result["details"] = {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1),
            }

            if free_gb < 10:
                result["status"] = "fail"
                result["message"] = f"磁盘空间不足: 剩余 {free_gb:.1f}GB"
            elif free_gb < 20:
                result["status"] = "warn"
                result["message"] = f"磁盘空间紧张: 剩余 {free_gb:.1f}GB"
            else:
                result["message"] = f"磁盘空间充足: 剩余 {free_gb:.1f}GB / {total_gb:.1f}GB"

        except Exception as e:
            result["status"] = "fail"
            result["message"] = f"无法检查磁盘空间: {e}"

        return result

    def check_network(self) -> dict:
        """检查网络连接"""
        result = {
            "status": "pass",
            "message": "网络连接正常",
            "details": {},
        }

        # 检查 GitHub 可达性
        hosts = [
            ("GitHub", "github.com", 443),
            ("HuggingFace", "huggingface.co", 443),
        ]

        for name, host, port in hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((host, port))
                sock.close()
                result["details"][name] = "reachable"
            except Exception:
                result["details"][name] = "unreachable"
                result["status"] = "warn"
                result["message"] = f"{name} 不可达"

        return result

    def check_dependencies(self) -> dict:
        """检查核心依赖是否安装"""
        result = {
            "status": "pass",
            "message": "",
            "details": {},
        }

        required_packages = [
            "PyQt6",
            "PyYAML",
            "requests",
            "packaging",
            "psutil",
            "colorama",
        ]

        missing = []
        for pkg in required_packages:
            try:
                __import__(pkg.replace("-", "_"))
                result["details"][pkg] = "installed"
            except ImportError:
                missing.append(pkg)
                result["details"][pkg] = "missing"

        if missing:
            result["status"] = "warn"
            result["message"] = f"缺少依赖: {', '.join(missing)}"
        else:
            result["message"] = "所有核心依赖已安装"

        return result

    def check_comfyui(self) -> dict:
        """检查 ComfyUI 安装状态"""
        result = {
            "status": "pass",
            "message": "",
            "details": {},
        }

        comfyui_dir = self._project_root / "comfyui"
        main_py = comfyui_dir / "main.py"

        result["details"]["exists"] = comfyui_dir.exists()
        result["details"]["main_py"] = main_py.exists()

        if not comfyui_dir.exists():
            result["status"] = "warn"
            result["message"] = "ComfyUI 尚未安装，请运行 'mcsp setup'"
        elif not main_py.exists():
            result["status"] = "fail"
            result["message"] = "ComfyUI 文件不完整"
        else:
            result["message"] = "ComfyUI 安装正常"

        return result

    def check_data_dirs(self) -> dict:
        """检查数据目录结构"""
        result = {
            "status": "pass",
            "message": "",
            "details": {},
        }

        expected_dirs = [
            "data/models",
            "data/workflows",
            "data/plugins",
            "data/logs",
            "configs",
        ]

        missing = []
        for dir_name in expected_dirs:
            dir_path = self._project_root / dir_name
            exists = dir_path.exists()
            result["details"][dir_name] = exists
            if not exists:
                missing.append(dir_name)

        if missing:
            result["status"] = "warn"
            result["message"] = f"缺少目录: {', '.join(missing)}"
        else:
            result["message"] = "数据目录结构完整"

        return result

    def get_summary(self) -> dict:
        """
        获取健康检查摘要

        Returns:
            摘要字典
        """
        results = self.run_all()
        statuses = [r["status"] for r in results.values()]

        summary = {
            "overall": "healthy",
            "total_checks": len(results),
            "passed": statuses.count("pass"),
            "warnings": statuses.count("warn"),
            "errors": statuses.count("fail"),
            "details": results,
        }

        if summary["errors"] > 0:
            summary["overall"] = "unhealthy"
        elif summary["warnings"] > 0:
            summary["overall"] = "degraded"

        return summary
