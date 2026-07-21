"""
虚拟环境管理模块

负责创建、检测和激活 Python 虚拟环境。
确保项目使用正确的 Python 版本和依赖。
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple
from src.logger import get_logger
from src.config_manager import get_config

logger = get_logger("env")


class EnvironmentManager:
    """
    虚拟环境管理器

    管理项目的 Python 虚拟环境创建、依赖安装和环境检测。
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化环境管理器

        Args:
            project_root: 项目根目录，默认为当前目录的上一级
        """
        if project_root is None:
            project_root = str(Path(__file__).parent.parent)
        self._project_root = Path(project_root)
        self._venv_dir = self._project_root / "venv"
        self._python_version = "3.11"
        self._min_python_version = (3, 11)

    @property
    def venv_dir(self) -> Path:
        """虚拟环境目录"""
        return self._venv_dir

    @property
    def python_executable(self) -> Path:
        """虚拟环境中 Python 解释器路径"""
        if platform.system() == "Windows":
            return self._venv_dir / "Scripts" / "python.exe"
        return self._venv_dir / "bin" / "python"

    @property
    def pip_executable(self) -> Path:
        """虚拟环境中 pip 可执行文件路径"""
        if platform.system() == "Windows":
            return self._venv_dir / "Scripts" / "pip.exe"
        return self._venv_dir / "bin" / "pip"

    def ensure_python_installed(self) -> Tuple[bool, str]:
        """
        检查 Python 3.11+ 是否已安装

        Returns:
            (是否已安装, Python 路径)
        """
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_str = result.stdout.strip().replace("Python ", "")
                version = tuple(map(int, version_str.split(".")[:2]))
                if version >= self._min_python_version:
                    logger.info(f"Python {version_str} 已安装")
                    return True, "python"
                else:
                    logger.warning(f"Python 版本过低: {version_str}，需要 >= 3.11")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 尝试 python3
        try:
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_str = result.stdout.strip().replace("Python ", "")
                version = tuple(map(int, version_str.split(".")[:2]))
                if version >= self._min_python_version:
                    logger.info(f"Python {version_str} 已安装")
                    return True, "python3"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        logger.error("未找到兼容的 Python 版本 (需要 3.11+)")
        return False, ""

    def ensure_venv(self, force: bool = False) -> bool:
        """
        确保虚拟环境存在

        Args:
            force: 如果虚拟环境已存在，是否强制重建

        Returns:
            是否成功
        """
        # 检查是否需要创建
        if self._venv_dir.exists() and not force:
            python_exe = self.python_executable
            if python_exe.exists():
                logger.info(f"虚拟环境已存在: {self._venv_dir}")
                return True

        # 创建虚拟环境
        logger.info(f"正在创建虚拟环境: {self._venv_dir}")

        cmd = [sys.executable, "-m", "venv", str(self._venv_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"创建虚拟环境失败: {result.stderr}")
            return False

        logger.info("虚拟环境创建成功")

        # 升级 pip
        self._upgrade_pip()

        return True

    def _upgrade_pip(self):
        """升级虚拟环境中的 pip"""
        logger.info("正在升级 pip...")
        cmd = [str(self.python_executable), "-m", "pip", "install", "--upgrade", "pip"]
        subprocess.run(cmd, capture_output=True, text=True)

    def install_requirements(self, requirements_file: Optional[str] = None) -> bool:
        """
        安装 requirements.txt 中的依赖

        Args:
            requirements_file: requirements 文件路径，默认为项目根目录下的 requirements.txt

        Returns:
            是否成功
        """
        if requirements_file is None:
            requirements_file = str(self._project_root / "requirements.txt")

        if not os.path.exists(requirements_file):
            logger.error(f"requirements 文件不存在: {requirements_file}")
            return False

        logger.info(f"正在安装依赖: {requirements_file}")

        cmd = [
            str(self.python_executable),
            "-m", "pip", "install",
            "-r", requirements_file,
            "--upgrade",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            logger.error(f"安装依赖失败: {result.stderr[-500:]}")
            return False

        logger.info("依赖安装成功")
        return True

    def install_xpu_requirements(self) -> bool:
        """安装 Intel XPU 相关的依赖"""
        logger.info("正在安装 Intel XPU 依赖...")
        return self.install_requirements(str(self._project_root / "requirements-xpu.txt"))

    def install_comfyui(self) -> bool:
        """
        克隆并安装 ComfyUI

        Returns:
            是否成功
        """
        comfyui_dir = self._project_root / "comfyui"

        if comfyui_dir.exists():
            logger.info("ComfyUI 已存在，跳过克隆")
            return True

        logger.info("正在克隆 ComfyUI...")

        # 从 GitHub 克隆
        result = subprocess.run(
            ["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(comfyui_dir)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.error(f"克隆 ComfyUI 失败: {result.stderr[:500]}")
            return False

        # 在虚拟环境中安装 ComfyUI
        logger.info("正在安装 ComfyUI 依赖...")
        cmd = [
            str(self.python_executable),
            "-m", "pip", "install", "-r", str(comfyui_dir / "requirements.txt"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            logger.error(f"安装 ComfyUI 依赖失败: {result.stderr[-500:]}")
            return False

        logger.info("ComfyUI 安装成功")
        return True

    def get_python_version(self) -> Optional[Tuple[int, int, int]]:
        """
        获取当前 Python 版本

        Returns:
            版本元组 (major, minor, micro)，或 None
        """
        try:
            result = subprocess.run(
                [str(self.python_executable), "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_str = result.stdout.strip().replace("Python ", "")
                parts = version_str.split(".")
                return (
                    int(parts[0]),
                    int(parts[1]),
                    int(parts[2]) if len(parts) > 2 else 0,
                )
        except Exception as e:
            logger.debug(f"获取 Python 版本失败: {e}")
        return None

    def is_venv_active(self) -> bool:
        """检查是否已在虚拟环境中运行"""
        return (
            getattr(sys, "real_prefix", None) is not None
            or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        )

    def get_env_status(self) -> dict:
        """
        获取环境状态摘要

        Returns:
            状态字典
        """
        python_installed, python_path = self.ensure_python_installed()
        venv_exists = self._venv_dir.exists()
        python_exe_exists = self.python_executable.exists()
        version = self.get_python_version()

        return {
            "python_installed": python_installed,
            "python_path": python_path,
            "venv_exists": venv_exists,
            "python_executable_exists": python_exe_exists,
            "python_version": version,
            "project_root": str(self._project_root),
            "venv_dir": str(self._venv_dir),
        }
