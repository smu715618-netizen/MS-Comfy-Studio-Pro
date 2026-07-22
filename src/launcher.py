"""launcher.py — 启动器核心模块

负责 ComfyUI 进程的启动、停止和管理。
整合硬件检测、环境管理、启动配置，提供统一的应用程序生命周期管理。
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger, setup_logging
from src.config_manager import ConfigManager
from src.gpu_detector import GPUDetector, GPUInfo, GPUType, SystemInfo
from src.cpu_monitor import CpuMonitor, MemoryMonitor, get_system_health
from src.start_config import LaunchConfigManager, VramMode
from src.env_manager import EnvironmentManager
from src.health_check import HealthChecker

logger = get_logger("launcher")


class LauncherState:
    """启动器状态管理 - 跟踪整个启动器的运行状态"""

    STATE_IDLE = "idle"
    STATE_CHECKING = "checking"
    STATE_STARTING = "starting"
    STATE_RUNNING = "running"
    STATE_STOPPING = "stopping"
    STATE_ERROR = "error"

    def __init__(self):
        self._state = self.STATE_IDLE
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @state.setter
    def state(self, value: str):
        with self._lock:
            old = self._state
            self._state = value
            logger.debug(f"State: {old} -> {value}")

    def is_idle(self) -> bool:
        return self._state == self.STATE_IDLE

    def is_running(self) -> bool:
        return self._state == self.STATE_RUNNING

    def is_busy(self) -> bool:
        return not self.is_idle()


class StartupConfig:
    """启动配置 - 根据硬件环境生成 ComfyUI 启动参数"""

    def __init__(self, config: ConfigManager, gpu_info: GPUInfo):
        self._config = config
        self._gpu = gpu_info
        self.port = config.get("comfyui.port", 8188)
        self.host = config.get("comfyui.host", "127.0.0.1")
        self.extra_args: List[str] = []
        self.vram_mode = self._detect_vram_mode()
        self._auto_optimize()

    def _detect_vram_mode(self) -> VramMode:
        mem_mb = self._gpu.memory_total_mb
        if mem_mb < 8192:
            return VramMode.LOW_VRAM
        elif mem_mb < 12288:
            return VramMode.NORMAL_VRAM
        elif mem_mb < 16384:
            return VramMode.HIGH_VRAM
        else:
            return VramMode.MAX_VRAM

    def _auto_optimize(self):
        """根据硬件自动生成优化参数"""
        mem_mb = self._gpu.memory_total_mb

        if mem_mb < 8192:
            self.extra_args.append("--low-vram")
            logger.info(f"Low VRAM mode: {mem_mb}MB < 8GB")
        elif mem_mb < 12288:
            self.extra_args.append("--normal-vram")
            logger.info(f"Normal VRAM mode: {mem_mb}MB")
        else:
            self.extra_args.append("--high-vram")
            logger.info(f"High VRAM mode: {mem_mb}MB")

        if self._gpu.xpu_supported:
            self.extra_args.append("--xpu")
            logger.info("Enabling Intel XPU acceleration")
        elif self._gpu.cuda_supported:
            self.extra_args.append("--cuda")
            logger.info("Enabling NVIDIA CUDA acceleration")
        elif self._gpu.directml_supported:
            self.extra_args.append("--directml")
            logger.info("Using DirectML fallback")

    def get_args(self) -> list:
        return ["--port", str(self.port), "--host", self.host] + self.extra_args

    def summary(self) -> dict:
        return {
            "port": self.port,
            "host": self.host,
            "gpu_type": self._gpu.gpu_type.value,
            "memory_mb": self._gpu.memory_total_mb,
            "vram_mode": self.vram_mode.value,
            "extra_args": self.extra_args,
        }


class ComfyUIProcess:
    """ComfyUI 进程管理器 - 管理 ComfyUI 服务的生命周期"""

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = str(_project_root)
        self._project_root = Path(project_root)
        self._comfyui_dir = self._project_root / "comfyui"
        self._main_py = self._comfyui_dir / "main.py"
        self._process: Optional[subprocess.Popen] = None
        self._status_callback: Optional[Callable] = None
        self._log_callback: Optional[Callable] = None

    def set_status_callback(self, callback: Callable):
        self._status_callback = callback

    def set_log_callback(self, callback: Callable):
        self._log_callback = callback

    def _notify_status(self, status: str):
        if self._status_callback:
            try:
                self._status_callback(status)
            except Exception as e:
                logger.error(f"Status callback failed: {e}")

    def _notify_log(self, message: str):
        if self._log_callback:
            try:
                self._log_callback(message)
            except Exception as e:
                logger.error(f"Log callback failed: {e}")

    @property
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def process_id(self) -> Optional[int]:
        if self._process:
            return self._process.pid
        return None

    def start(self, config: StartupConfig) -> bool:
        """启动 ComfyUI"""
        if self.is_running:
            logger.warning("ComfyUI is already running")
            return False

        if not self._main_py.exists():
            logger.error(f"ComfyUI not found: {self._main_py}")
            logger.error("Please run 'python setup_comfyui.bat' to install ComfyUI")
            return False

        cmd = [sys.executable, str(self._main_py)] + config.get_args()
        logger.info(f"Starting ComfyUI on port {config.port}...")
        logger.info(f"Command: {' '.join(cmd)}")

        self._notify_status("starting")

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._comfyui_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            t = threading.Thread(target=self._read_stdout, daemon=True)
            t.start()

            time.sleep(5)

            if self._process.poll() is not None:
                logger.error("ComfyUI exited immediately after start")
                self._process = None
                self._notify_status("error")
                return False

            self._notify_status("running")
            logger.info(f"ComfyUI started (PID: {self._process.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            self._notify_status("error")
            return False

    def _read_stdout(self):
        """后台读取输出流"""
        if self._process and self._process.stdout:
            for line in self._process.stdout:
                line = line.strip()
                if line and self._log_callback:
                    try:
                        self._log_callback(line)
                    except:
                        pass

    def stop(self) -> bool:
        """停止 ComfyUI"""
        if not self.is_running:
            logger.warning("ComfyUI is not running")
            return False

        logger.info("Stopping ComfyUI...")
        self._notify_status("stopping")

        try:
            pid = self._process.pid
            os.popen(f'taskkill /F /T /PID {pid}')
            self._process.wait(timeout=15)
            self._process = None
            self._notify_status("stopped")
            logger.info("ComfyUI stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop ComfyUI: {e}")
            self._notify_status("error")
            return False

    def restart(self, port: Optional[int] = None) -> bool:
        """重启 ComfyUI"""
        self.stop()
        time.sleep(2)
        return False  # Needs config parameter


class DashboardData:
    """仪表盘数据 - 汇总各模块信息供 UI 显示"""

    def __init__(self):
        self._gpu_detector = GPUDetector()
        self._env_mgr = EnvironmentManager(_project_root)
        self._health_checker = HealthChecker(_project_root)

    def get_full_report(self) -> Dict[str, Any]:
        """获取完整的仪表盘数据"""
        gpu = self._gpu_detector.detect()
        sys_info = self._gpu_detector.get_system_info()
        health = self._health_checker.get_summary()

        return {
            "gpu": {
                "type": gpu.gpu_type.value,
                "name": gpu.name or "Unknown",
                "memory_mb": gpu.memory_total_mb,
                "xpu_available": gpu.xpu_supported,
                "cuda_available": gpu.cuda_supported,
                "directml_available": gpu.directml_supported,
            },
            "system": {
                "cpu_name": sys_info.cpu_name,
                "cpu_cores_physical": sys_info.cpu_cores_physical,
                "cpu_cores_logical": sys_info.cpu_cores_logical,
                "total_memory_mb": sys_info.total_memory_mb,
                "available_memory_mb": sys_info.available_memory_mb,
                "python_version": sys_info.python_version,
                "os_name": sys_info.os_name,
                "os_version": sys_info.os_version,
            },
            "comfyui": {
                "installed": (Path(_project_root) / "comfyui" / "main.py").exists(),
                "running": False,  # Updated by Launcher
            },
            "health": health,
        }


class Launcher:
    """主启动器类 - 整合所有模块提供统一接口"""

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = str(_project_root)

        self._project_root = Path(project_root)
        self._config = ConfigManager()

        # 核心组件
        self._state = LauncherState()
        self._dashboard = DashboardData()
        self._launch_config_mgr = LaunchConfigManager()
        self._comfy_process: Optional[ComfyUIProcess] = None
        self._startup_config: Optional[StartupConfig] = None

        # 回调
        self._status_callback: Optional[Callable] = None
        self._log_callback: Optional[Callable] = None

    @property
    def state(self) -> str:
        return self._state.state

    # ---- 公共 API ----

    def health_check(self) -> dict:
        """执行完整健康检查"""
        self._state.state = LauncherState.STATE_CHECKING
        try:
            result = self._dashboard._health_checker.get_summary()
            self._state.state = LauncherState.STATE_IDLE
            return result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._state.state = LauncherState.STATE_IDLE
            return {"overall": "error", "error": str(e)}

    def start_comfyui(self, port: Optional[int] = None) -> bool:
        """一键启动 ComfyUI（自动选择最优配置）"""
        if self._state.is_busy():
            logger.warning(f"Cannot start while in state: {self._state.state}")
            return False

        if self._state.is_running():
            logger.warning("ComfyUI is already running")
            return False

        logger.info("Checking environment before launch...")
        self._state.state = LauncherState.STATE_CHECKING

        # 1. 检测 GPU
        gpu_info = self._dashboard._gpu_detector.detect()
        if gpu_info.gpu_type == GPUType.CPU_ONLY:
            logger.warning("No GPU detected, will use CPU mode (slow)")

        # 2. 生成启动配置
        self._startup_config = StartupConfig(self._config, gpu_info)
        if port:
            self._startup_config.port = port

        # 3. 验证 ComfyUI
        comfyui_main = self._project_root / "comfyui" / "main.py"
        if not comfyui_main.exists():
            logger.error("ComfyUI not installed. Run 'setup_comfyui.bat' first.")
            self._state.state = LauncherState.STATE_IDLE
            return False

        # 4. 启动
        logger.info("Starting ComfyUI...")
        self._state.state = LauncherState.STATE_STARTING

        self._comfy_process = ComfyUIProcess()
        self._comfy_process.set_log_callback(self._forward_log)

        success = self._comfy_process.start(self._startup_config)
        if success:
            self._state.state = LauncherState.STATE_RUNNING
            logger.info("ComfyUI started successfully!")
        else:
            self._state.state = LauncherState.STATE_IDLE
            logger.error("ComfyUI failed to start")

        return success

    def stop_comfyui(self) -> bool:
        """停止 ComfyUI"""
        if self._state.state != LauncherState.STATE_RUNNING:
            logger.warning("ComfyUI is not running")
            return False

        self._state.state = LauncherState.STATE_STOPPING
        logger.info("Stopping ComfyUI...")

        success = False
        if self._comfy_process:
            success = self._comfy_process.stop()

        if success:
            self._state.state = LauncherState.STATE_IDLE
            logger.info("ComfyUI stopped")
        else:
            self._state.state = LauncherState.STATE_ERROR
            logger.error("Stop failed")

        return success

    def get_dashboard_data(self) -> dict:
        """获取首页仪表盘数据"""
        data = self._dashboard.get_full_report()
        data["comfyui"]["running"] = self._state.is_running()
        data["launcher_state"] = self._state.state
        return data

    def get_launch_recommendation(self) -> dict:
        """获取启动配置推荐"""
        return self._launch_config_mgr.get_recommended_config()

    # ---- 内部方法 ----

    def _forward_log(self, message: str):
        if self._log_callback:
            self._log_callback(message)

    def on_status_change(self, callback: Callable[[str], None]):
        self._status_callback = callback

    def on_log_message(self, callback: Callable[[str], None]):
        self._log_callback = callback


def run_launcher_cli(project_root: str = None):
    """命令行模式：通过终端启动/停止 ComfyUI"""
    launcher = Launcher(project_root)

    print("=" * 50)
    print("  MS Comfy Studio Pro - Launcher CLI")
    print("=" * 50)
    print()

    while True:
        print("Actions:")
        print("  1. Health Check")
        print("  2. Start ComfyUI")
        print("  3. Stop ComfyUI")
        print("  4. Show Dashboard")
        print("  5. Exit")
        print()
        choice = input("Choose [1-5]: ").strip()

        if choice == "1":
            result = launcher.health_check()
            print(f"\nResult: {result['overall']}")
            for k, v in result.get("details", {}).items():
                print(f"  {k}: {v.get('message', '')}")

        elif choice == "2":
            port_input = input("Port (Enter for default 8188): ").strip()
            port = int(port_input) if port_input.isdigit() else None
            launcher.start_comfyui(port=port)

        elif choice == "3":
            launcher.stop_comfyui()

        elif choice == "4":
            data = launcher.get_dashboard_data()
            gpu = data["gpu"]
            sys_data = data["system"]
            print(f"\nGPU: {gpu['name']} ({gpu['memory_mb']}MB)")
            print(f"CPU: {sys_data['cpu_cores_logical']} cores")
            print(f"RAM: {sys_data['available_memory_mb']}MB / {sys_data['total_memory_mb']}MB free")
            print(f"ComfyUI: {data['comfyui']['state']}")
            print(f"Python: {sys_data['python_version']}")

        elif choice == "5":
            if launcher._state.is_running():
                launcher.stop_comfyui()
            print("Goodbye!")
            break


if __name__ == "__main__":
    run_launcher_cli()
