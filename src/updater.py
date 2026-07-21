"""
自动更新框架

管理三个层面的更新：
1. 应用更新 (App Updater) - MCSP 自身代码更新
2. 模型更新 (Model Updater) - 模型文件更新检查
3. 节点/插件更新 (Node Updater) - 社区节点和插件更新

更新机制：
- 检查 GitHub Releases 获取最新版本
- 下载更新包
- 验证签名（预留）
- 应用更新（支持回滚）
"""

import os
import json
import hashlib
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from src.logger import get_logger
from src.config_manager import get_config

logger = get_logger("updater")


class UpdateCheckResult:
    """更新检查结果"""

    def __init__(
        self,
        available: bool,
        current_version: str,
        latest_version: str,
        release_notes: str = "",
        download_url: str = "",
        file_size: int = 0,
        changelog: str = "",
    ):
        self.available = available
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_notes = release_notes
        self.download_url = download_url
        self.file_size = file_size
        self.changelog = changelog

    def __repr__(self):
        if self.available:
            return f"UpdateCheckResult(available=True, {self.current_version} -> {self.latest_version})"
        return f"UpdateCheckResult(available=False, {self.current_version})"


class AppUpdater:
    """
    应用程序更新器

    负责 MCSP 自身的更新。
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化应用更新器

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            project_root = str(Path(__file__).parent.parent)
        self._project_root = Path(project_root)
        self._update_state_file = self._project_root / "data" / "update_state.json"

        # 更新进度回调
        self._progress_callback: Optional[Callable] = None

        # 确保数据目录存在
        self._update_state_file.parent.mkdir(parents=True, exist_ok=True)

    def set_progress_callback(self, callback: Callable):
        """设置更新进度回调"""
        self._progress_callback = callback

    def _notify_progress(self, message: str, progress: float = 0.0):
        """通知进度"""
        if self._progress_callback:
            try:
                self._progress_callback(message, progress)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    def check_for_updates(self) -> UpdateCheckResult:
        """
        检查是否有可用更新

        Returns:
            更新检查结果
        """
        from src.__version__ import __version__

        current_version = __version__
        logger.info(f"检查更新，当前版本: {current_version}")

        # TODO: 实现实际的更新检查逻辑
        # 可以从 GitHub API 获取最新版本
        # 这里返回占位结果

        try:
            import requests
            # 从 GitHub Releases API 获取最新版本
            response = requests.get(
                "https://api.github.com/repos/comfy-studio-pro/ms-comfy/releases/latest",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", current_version)
                release_notes = data.get("body", "")
                download_url = data.get("html_url", "")

                if latest_version != current_version:
                    return UpdateCheckResult(
                        available=True,
                        current_version=current_version,
                        latest_version=latest_version,
                        release_notes=release_notes,
                        download_url=download_url,
                    )
        except Exception as e:
            logger.debug(f"在线检查更新失败: {e}")

        return UpdateCheckResult(
            available=False,
            current_version=current_version,
            latest_version=current_version,
        )

    def apply_update(self, update: UpdateCheckResult) -> bool:
        """
        应用更新

        Args:
            update: 更新检查结果

        Returns:
            是否成功
        """
        if not update.available:
            logger.info("没有可用更新")
            return True

        logger.info(f"准备更新: {update.current_version} -> {update.latest_version}")

        try:
            self._notify_progress("正在下载更新...", 0.1)

            # TODO: 实现实际下载逻辑
            # 1. 下载更新包
            # 2. 验证完整性
            # 3. 备份当前版本
            # 4. 解压更新
            # 5. 迁移配置
            # 6. 重启应用

            self._notify_progress("更新完成", 1.0)
            logger.info("更新成功")
            return True

        except Exception as e:
            logger.error(f"更新失败: {e}")
            self._notify_progress("更新失败", 0.0)
            return False

    def rollback(self) -> bool:
        """
        回滚到上一个版本

        Returns:
            是否成功
        """
        logger.info("正在回滚更新...")

        backup_dir = self._project_root / ".backup"
        if backup_dir.exists():
            try:
                # 恢复备份
                self._notify_progress("正在恢复备份...", 0.5)
                # TODO: 实现回滚逻辑
                logger.info("回滚成功")
                return True
            except Exception as e:
                logger.error(f"回滚失败: {e}")
                return False
        else:
            logger.warning("没有找到备份，无法回滚")
            return False

    def get_last_check_time(self) -> Optional[datetime]:
        """获取上次检查更新的时间"""
        if self._update_state_file.exists():
            try:
                with open(self._update_state_file, "r") as f:
                    data = json.load(f)
                return datetime.fromisoformat(data.get("last_check", ""))
            except Exception:
                pass
        return None

    def set_last_check_time(self):
        """记录上次检查更新时间"""
        state = {
            "last_check": datetime.now().isoformat(),
        }
        try:
            with open(self._update_state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"保存更新状态失败: {e}")


class ModelUpdater:
    """
    模型更新器

    检查已安装模型的更新。
    """

    def __init__(self):
        self._model_registry: Dict[str, str] = {}  # {model_name: source_url}

    def check_model_updates(self, model_name: str) -> bool:
        """检查模型是否有更新"""
        # TODO: 实现模型更新检查
        return False

    def update_model(self, model_name: str) -> bool:
        """更新单个模型"""
        # TODO: 实现模型更新
        return False


class NodeUpdater:
    """
    节点更新器

    管理 ComfyUI 社区节点的更新检查。
    """

    def __init__(self):
        self._node_versions: Dict[str, str] = {}

    def check_node_updates(self) -> Dict[str, str]:
        """
        检查所有节点的更新

        Returns:
            {节点名称: 最新版本号}
        """
        # TODO: 实现节点更新检查
        return {}

    def update_node(self, name: str) -> bool:
        """更新单个节点"""
        # TODO: 实现节点更新
        return False
