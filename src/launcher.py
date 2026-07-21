"""
启动器核心模块

负责 ComfyUI 进程的启动、停止和管理。
包含进程监控、日志捕获和状态追踪。
"""

import os
import sys
import subprocess
import signal
import time
import platform
from pathlib import Path
from typing import Optional, Callable
from src.logger import get_logger
from src.config_manager import get_config

logger = get_logger("launcher")


class ComfyUIProcess:
    """
    ComfyUI 进程管理器

    管理 ComfyUI 服务的生命周期：
    - 启动
    - 停止
    - 状态监控
    - 日志捕获
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化进程管理器

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            project_root = str(Path(__file__).parent.parent)
        self._project_root = Path(project_root)
        self._comfyui_dir = self._project_root / "comfyui"
        self._process: Optional[subprocess.Popen] = None
        self._config = get_config()

        # 状态回调
        self._status_callback: Optional[Callable] = None
        self._log_callback: Optional[Callable] = None

    def set_status_callback(self, callback: Callable):
        """设置状态变化回调 (status: str) -> None"""
        self._status_callback = callback

    def set_log_callback(self, callback: Callable):
        """设置日志回调 (message: str) -> None"""
        self._log_callback = callback

    def _notify_status(self, status: str):
        """通知状态变化"""
        if self._status_callback:
            try:
                self._status_callback(status)
            except Exception as e:
                logger.error(f"状态回调失败: {e}")

    def _notify_log(self, message: str):
        """通知日志消息"""
        if self._log_callback:
            try:
                self._log_callback(message)
            except Exception as e:
                logger.error(f"日志回调失败: {e}")

    @property
    def is_running(self) -> bool:
        """ComfyUI 是否正在运行"""
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def process_id(self) -> Optional[int]:
        """进程 PID"""
        if self._process:
            return self._process.pid
        return None

    def start(
        self,
        port: Optional[int] = None,
        extra_args: Optional[list] = None,
    ) -> bool:
        """
        启动 ComfyUI

        Args:
            port: 端口号
            extra_args: 额外启动参数

        Returns:
            是否成功启动
        """
        if self.is_running:
            logger.warning("ComfyUI 已经在运行")
            return False

        main_py = self._comfyui_dir / "main.py"
        if not main_py.exists():
            logger.error(f"找不到 ComfyUI: {main_py}")
            return False

        # 确定端口
        if port is None:
            port = self._config.get("comfyui.port", 8188)

        # 构建命令
        cmd = [
            sys.executable,
            str(main_py),
            "--port", str(port),
        ]

        if extra_args:
            cmd.extend(extra_args)

        logger.info(f"正在启动 ComfyUI (端口: {port})")
        logger.info(f"命令: {' '.join(str(c) for c in cmd)}")

        self._notify_status("starting")

        # 启动进程
        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._comfyui_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # 启动日志读取线程
            import threading
            t = threading.Thread(target=self._read_stdout, daemon=True)
            t.start()

            # 等待几秒确认启动成功
            time.sleep(3)

            if self._process.poll() is not None:
                logger.error("ComfyUI 启动后立即退出")
                self._process = None
                self._notify_status("error")
                return False

            self._notify_status("running")
            logger.info(f"ComfyUI 已启动 (PID: {self._process.pid})")
            return True

        except Exception as e:
            logger.error(f"启动 ComfyUI 失败: {e}")
            self._notify_status("error")
            return False

    def _read_stdout(self):
        """读取进程标准输出的线程函数"""
        if self._process is None:
            return
        try:
            for line in self._process.stdout:
                line = line.rstrip("\n\r")
                if line:
                    self._notify_log(line)
        except Exception as e:
            logger.error(f"读取 ComfyUI 输出失败: {e}")

    def stop(self) -> bool:
        """
        停止 ComfyUI

        Returns:
            是否成功停止
        """
        if not self.is_running:
            logger.warning("ComfyUI 未在运行")
            return False

        logger.info("正在停止 ComfyUI...")
        self._notify_status("stopping")

        try:
            if platform.system() == "Windows":
                # Windows: 终止进程树
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                self._process.terminate()

            # 等待进程退出
            try:
                self._process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                logger.warning("进程未响应，强制终止")
                self._process.kill()
                self._process.wait()

            self._process = None
            self._notify_status("stopped")
            logger.info("ComfyUI 已停止")
            return True

        except Exception as e:
            logger.error(f"停止 ComfyUI 失败: {e}")
            self._notify_status("error")
            return False

    def restart(self, port: Optional[int] = None) -> bool:
        """重启 ComfyUI"""
        self.stop()
        time.sleep(1)
        return self.start(port=port)
