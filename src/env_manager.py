"""env_manager.py — 虚拟环境管理与Intel运行环境检测

负责：
1. Python 环境检测（版本、安装位置、虚拟环境）
2. Intel XPU / OneAPI / IPEX 环境检测
3. ComfyUI 安装状态管理
4. 依赖包安装管理

设计原则：
- 仅检测，不自动修改用户系统环境
- 所有操作可逆
- 模块解耦，不默认加载任何GPU后端
- 按需激活，用完即释放

"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger

logger = get_logger("env")


# ================================================================
# 数据结构
# ================================================================

@dataclass
class PythonInfo:
    """Python 环境信息"""
    version_str: str = ""
    version_tuple: Tuple[int, int, int] = (0, 0, 0)
    path: str = ""
    is_64bit: bool = False
    virtualenv: bool = False
    min_version_ok: bool = False


@dataclass
class IntelRuntimeInfo:
    """Intel 运行时环境信息"""
    oneapi_installed: bool = False
    oneapi_version: str = ""
    ipex_available: bool = False
    ipex_version: str = ""
    openvino_available: bool = False
    xpu_driver_available: bool = False
    xpu_driver_version: str = ""
    issues: List[str] = field(default_factory=list)


@dataclass
class ComfyUIInfo:
    """ComfyUI 安装状态"""
    installed: bool = False
    directory: str = ""
    main_py_exists: bool = False
    git_repo: bool = False
    last_commit: str = ""
    branch: str = ""


@dataclass
class InstalledPackage:
    """已安装包信息"""
    name: str
    version: str
    install_path: str = ""


@dataclass
class EnvStatus:
    """完整环境状态"""
    python: PythonInfo = field(default_factory=PythonInfo)
    intel_runtime: IntelRuntimeInfo = field(default_factory=IntelRuntimeInfo)
    comfyui: ComfyUIInfo = field(default_factory=ComfyUIInfo)
    required_packages: List[InstalledPackage] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)
    venv_dir: str = ""
    project_root: str = ""


# ================================================================
# Python 环境检测
# ================================================================

class PythonDetector:
    """Python 环境检测器"""

    MIN_VERSION = (3, 11, 0)
    RECOMMENDED_VERSION = (3, 11, 9)

    @staticmethod
    def detect() -> PythonInfo:
        info = PythonInfo(
            version_str=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            version_tuple=sys.version_info[:3],
            path=sys.executable,
            is_64bit=(sys.maxsize > 2**32),
            virtualenv=sys.prefix != sys.base_prefix,
            min_version_ok=sys.version_info >= PythonDetector.MIN_VERSION,
        )
        if not info.min_version_ok:
            logger.warning(f"Python {info.version_str} < 3.11，可能不兼容")
        return info

    @staticmethod
    def system_python_available() -> Tuple[bool, str]:
        """检测系统是否有独立安装的 Python"""
        candidates = ["python", "python3"]
        for cmd in candidates:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    ver = result.stdout.strip().replace("Python ", "")
                    return True, ver
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False, ""


# ================================================================
# Intel 运行时检测
# ================================================================

class IntelRuntimeDetector:
    """Intel GPU 运行时环境检测"""

    @staticmethod
    def detect(project_root: Path) -> IntelRuntimeInfo:
        info = IntelRuntimeInfo()

        # 1. 检查 Intel 驱动是否就绪（通过 DirectX/WMI）
        info.xpu_driver_available = IntelRuntimeDetector._check_xpu_driver()
        if info.xpu_driver_available:
            info.xpu_driver_version = IntelRuntimeDetector._get_driver_version() or "unknown"

        # 2. 检查 OneAPI 是否在 PATH 中
        info.oneapi_installed = IntelRuntimeDetector._check_oneapi()
        if info.oneapi_installed:
            info.oneapi_version = IntelRuntimeDetector._get_oneapi_version() or "unknown"

        # 3. 检查 PyTorch IPEX 模块是否可用
        try:
            import torch
            has_ipex = hasattr(torch, 'xpu') and torch.xpu.is_available()
            if has_ipex:
                info.ipex_available = True
                info.ipex_version = torch.__version__
        except ImportError:
            pass  # PyTorch 未安装，正常情况

        # 4. OpenVINO 预留检测
        # TODO: 未来实现

        # 生成问题报告
        if not info.xpu_driver_available:
            info.issues.append(
                "未检测到 Intel Arc 显卡驱动。请前往 Intel 驱动中心更新驱动。"
            )

        return info

    @staticmethod
    def _check_xpu_driver() -> bool:
        """通过 PowerShell 查询 Win32_VideoController"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | "
                 "Where-Object {$_.Name -like '*Arc*' -or $_.Name -like '*Intel*'} | "
                 "Select-Object -First 1 Name, DriverVersion | Format-List"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0 and ("Arc" in result.stdout or "Intel" in result.stdout)
        except Exception:
            return False

    @staticmethod
    def _get_driver_version() -> str:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_VideoController | "
                 "Where-Object {$_.Name -like '*Arc*'}).DriverVersion"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return ""

    @staticmethod
    def _check_oneapi() -> bool:
        """检查 OneAPI 环境变量"""
        return (os.environ.get("ONEAPI_ROOT") is not None
                or os.environ.get("LEVEL_ZERO_PATH") is not None
                or os.environ.get("ZE_TRACE_LEVEL") is not None)

    @staticmethod
    def _get_oneapi_version() -> str:
        root = os.environ.get("ONEAPI_ROOT", "")
        if not root:
            return ""
        try:
            ver_file = Path(root) / "version.txt"
            if ver_file.exists():
                return ver_file.read_text().strip()
        except Exception:
            pass
        return root


# ================================================================
# ComfyUI 管理
# ================================================================

class ComfyUIManager:
    """ComfyUI 安装/更新管理"""

    @staticmethod
    def check_status(project_root: Path) -> ComfyUIInfo:
        info = ComfyUIInfo()
        comfyui_dir = project_root / "comfyui"

        info.directory = str(comfyui_dir)
        info.installed = comfyui_dir.exists()
        info.main_py_exists = (comfyui_dir / "main.py").exists()
        info.git_repo = (comfyui_dir / ".git").exists()

        if info.git_repo:
            try:
                result = subprocess.run(
                    ["git", "-C", str(comfyui_dir), "log", "-1", "--format=%h"],
                    capture_output=True, text=True, timeout=10
                )
                info.last_commit = result.stdout.strip()

                result2 = subprocess.run(
                    ["git", "-C", str(comfyui_dir), "branch", "--show-current"],
                    capture_output=True, text=True, timeout=10
                )
                info.branch = result2.stdout.strip()
            except Exception:
                pass

        return info

    @staticmethod
    def install(project_root: Path) -> bool:
        comfyui_dir = project_root / "comfyui"
        if comfyui_dir.exists():
            logger.info("ComfyUI 已存在，跳过克隆")
            return True

        logger.info("正在克隆 ComfyUI...")
        result = subprocess.run(
            ["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(comfyui_dir)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            logger.error(f"克隆失败: {result.stderr[:500]}")
            return False
        logger.info("ComfyUI 克隆成功")
        return True

    @staticmethod
    def update(project_root: Path) -> bool:
        comfyui_dir = project_root / "comfyui"
        if not comfyui_dir.exists():
            logger.error("ComfyUI 未安装，无法更新")
            return False

        logger.info("正在更新 ComfyUI...")
        result = subprocess.run(
            ["git", "-C", str(comfyui_dir), "pull"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            logger.error(f"更新失败: {result.stderr[:500]}")
            return False
        logger.info("ComfyUI 更新成功")
        return True


# ================================================================
# 依赖包管理
# ================================================================

class PackageManager:
    """包安装管理"""

    REQUIRED_PACKAGES = [
        "PyQt6", "PyYAML", "requests", "packaging", "psutil", "colorama",
    ]
    OPTIONAL_XPU_PACKAGES = [
        "torch-directml",  # DirectML 支持
    ]

    @staticmethod
    def check_installed(pip_exe: Path) -> List[InstalledPackage]:
        installed = []
        try:
            result = subprocess.run(
                [str(pip_exe), "list", "--format=json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)
                for pkg in packages:
                    installed.append(InstalledPackage(
                        name=pkg["name"],
                        version=pkg["version"],
                        install_path=str(Path(pip_exe).parent.parent / pkg["name"]),
                    ))
        except Exception as e:
            logger.debug(f"获取包列表失败: {e}")
        return installed

    @staticmethod
    def check_required(pip_exe: Path) -> Tuple[List[str], List[InstalledPackage]]:
        """检查必需包是否安装"""
        installed = {p.name.lower().replace("-", "_"): p for p in PackageManager.check_installed(pip_exe)}
        missing = []
        present = []

        for pkg_name in PackageManager.REQUIRED_PACKAGES:
            normalized = pkg_name.lower().replace("-", "_")
            if normalized in installed:
                present.append(installed[normalized])
            else:
                missing.append(pkg_name)

        return missing, present

    @staticmethod
    def install_requirements(pip_exe: Path, req_file: Path) -> bool:
        if not req_file.exists():
            logger.error(f"requirements 文件不存在: {req_file}")
            return False

        logger.info(f"正在安装依赖: {req_file.name}")
        cmd = [str(pip_exe), "install", "-r", str(req_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"安装失败: {result.stderr[-500:]}")
            return False
        logger.info(f"依赖安装成功: {req_file.name}")
        return True

    @staticmethod
    def reinstall_package(pip_exe: Path, package_name: str) -> bool:
        """重新安装单个包"""
        logger.info(f"重新安装包: {package_name}")
        cmd = [str(pip_exe), "install", "--force-reinstall", package_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"重装失败: {result.stderr[:300]}")
            return False
        logger.info(f"包已重新安装: {package_name}")
        return True


# ================================================================
# 主管理类
# ================================================================

class EnvironmentManager:
    """
    环境管理器 — 统一管理 Python/Intel/ComfyUI/依赖

    所有检测方法均为只读操作，不会修改用户系统。
    """

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = str(_project_root)
        self._project_root = Path(project_root)
        self._venv_dir = self._project_root / "venv"

    @property
    def project_root(self) -> Path:
        return self._project_root

    @property
    def venv_dir(self) -> Path:
        return self._venv_dir

    @property
    def python_executable(self) -> Path:
        win = platform.system() == "Windows"
        return self._venv_dir / "Scripts" / "python.exe" if win else self._venv_dir / "bin" / "python"

    @property
    def pip_executable(self) -> Path:
        win = platform.system() == "Windows"
        return self._venv_dir / "Scripts" / "pip.exe" if win else self._venv_dir / "bin" / "pip"

    def create_venv(self, force: bool = False) -> bool:
        """创建 Python 虚拟环境"""
        if self._venv_dir.exists() and not force:
            logger.info(f"虚拟环境已存在: {self._venv_dir}")
            return True
        logger.info(f"正在创建虚拟环境: {self._venv_dir}")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(self._venv_dir)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"创建失败: {result.stderr}")
            return False
        self._upgrade_pip()
        return True

    def ensure_venv_and_deps(self) -> Tuple[bool, List[str]]:
        """
        一键检查并修复环境

        Returns:
            (是否全部OK, 问题列表)
        """
        warnings = []

        # 1. 虚拟环境
        if not self._venv_dir.exists():
            warnings.append("虚拟环境未创建，建议运行 'mcsp setup'")

        # 2. Python 版本
        py = PythonDetector.detect()
        if not py.min_version_ok:
            warnings.append(f"Python {py.version_str} 低于 3.11")

        # 3. Intel 驱动
        intel = IntelRuntimeDetector.detect(self._project_root)
        if intel.issues:
            warnings.extend(intel.issues)

        # 4. ComfyUI
        cu = ComfyUIManager.check_status(self._project_root)
        if not cu.installed:
            warnings.append("ComfyUI 未安装")

        return len(warnings) == 0, warnings

    def get_full_status(self) -> dict:
        """获取完整环境状态摘要（供 Dashboard 显示）"""
        py = PythonDetector.detect()
        intel = IntelRuntimeDetector.detect(self._project_root)
        cu = ComfyUIManager.check_status(self._project_root)

        pip = self.pip_executable
        _, missing = PackageManager.check_required(pip) if pip.exists() else ([], [])

        return {
            "python": {
                "version": py.version_str,
                "path": py.path,
                "is_64bit": py.is_64bit,
                "virtualenv": py.virtualenv,
                "min_version_ok": py.min_version_ok,
            },
            "intel": {
                "driver_available": intel.xpu_driver_available,
                "driver_version": intel.xpu_driver_version,
                "oneapi_installed": intel.oneapi_installed,
                "ipex_available": intel.ipex_available,
                "issues": intel.issues,
            },
            "comfyui": {
                "installed": cu.installed,
                "main_py_exists": cu.main_py_exists,
                "last_commit": cu.last_commit,
                "branch": cu.branch,
            },
            "dependencies": {
                "missing": missing,
            },
        }

    # ---- 内部方法 ----

    def _upgrade_pip(self):
        pip_exe = self.python_executable
        if pip_exe.exists():
            subprocess.run(
                [str(pip_exe), "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True, text=True
            )


if __name__ == "__main__":
    mgr = EnvironmentManager()
    status = mgr.get_full_status()
    print(f"Python:   {status['python']['version']}")
    print(f"Intel:    driver={'OK' if status['intel']['driver_available'] else 'N/A'}")
    print(f"ComfyUI:  {'installed' if status['comfyui']['installed'] else 'not installed'}")
    print(f"Deps:     missing={status['dependencies']['missing']}")
