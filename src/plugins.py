"""
插件管理框架

管理 ComfyUI 插件（自定义节点包）的生命周期：
- 插件安装（从 GitHub / PyPI）
- 插件更新
- 插件卸载
- 插件启用/禁用
- 插件依赖管理
- 插件元数据解析

插件目录: data/plugins/
每个插件是一个独立的 git 仓库或 Python 包。
"""

import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional
from src.logger import get_logger
from src.config_manager import get_config

logger = get_logger("plugins")


class PluginSource(Enum):
    """插件来源"""
    GITHUB = "github"      # 从 GitHub 安装
    PYPI = "pypi"          # 从 PyPI 安装
    LOCAL = "local"        # 本地安装


class PluginStatus(Enum):
    """插件状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    OUTDATED = "outdated"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str                          # 插件名称
    source: PluginSource               # 来源
    status: PluginStatus = PluginStatus.ACTIVE
    version: str = ""                  # 当前版本
    latest_version: str = ""           # 最新版本
    description: str = ""              # 描述
    author: str = ""                   # 作者
    repo_url: str = ""                 # 仓库 URL
    pypi_name: str = ""                # PyPI 包名
    requirements: List[str] = field(default_factory=list)  # Python 依赖
    enabled: bool = True               # 是否启用
    directory: str = ""                # 安装目录
    installed_at: str = ""             # 安装时间

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PluginInfo":
        data = data.copy()
        if "source" in data:
            data["source"] = PluginSource(data["source"])
        if "status" in data:
            data["status"] = PluginStatus(data["status"])
        return cls(**data)


class PluginManager:
    """
    插件管理器

    管理 ComfyUI 的第三方插件安装和生命周期。
    """

    def __init__(self, plugins_dir: Optional[str] = None):
        """
        初始化插件管理器

        Args:
            plugins_dir: 插件存储目录
        """
        if plugins_dir is None:
            plugins_dir = str(Path(__file__).parent.parent / "data" / "plugins")

        self._plugins_dir = Path(plugins_dir)
        self._index_file = self._plugins_dir / "index.json"

        # 插件索引
        self._plugins: Dict[str, PluginInfo] = {}

        # 确保目录存在
        self._plugins_dir.mkdir(parents=True, exist_ok=True)

        # 加载索引
        self._load_index()

    def _load_index(self):
        """加载插件索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, info in data.items():
                    self._plugins[name] = PluginInfo.from_dict(info)
                logger.info(f"已加载 {len(self._plugins)} 个插件")
            except Exception as e:
                logger.error(f"加载插件索引失败: {e}")

    def _save_index(self):
        """保存插件索引"""
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {name: info.to_dict() for name, info in self._plugins.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"保存插件索引失败: {e}")

    def install_from_github(self, repo_url: str) -> bool:
        """
        从 GitHub 安装插件

        Args:
            repo_url: Git 仓库 URL

        Returns:
            是否成功
        """
        # 从 URL 提取插件名称
        repo_name = repo_url.rstrip("/").split("/")[-1]
        # 去除 .git 后缀
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        if repo_name in self._plugins:
            logger.warning(f"插件已安装: {repo_name}")
            return False

        target_dir = self._plugins_dir / repo_name

        logger.info(f"正在安装插件: {repo_name} ({repo_url})")

        result = subprocess.run(
            ["git", "clone", repo_url, str(target_dir)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.error(f"安装失败: {result.stderr[:500]}")
            return False

        # 解析插件元数据
        info = self._parse_plugin_metadata(target_dir, repo_name, repo_url)

        self._plugins[repo_name] = info
        self._save_index()
        logger.info(f"插件安装成功: {repo_name}")
        return True

    def install_from_pypi(self, package_name: str) -> bool:
        """
        从 PyPI 安装插件

        Args:
            package_name: PyPI 包名

        Returns:
            是否成功
        """
        logger.info(f"正在从 PyPI 安装: {package_name}")

        result = subprocess.run(
            ["pip", "install", package_name],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.error(f"PyPI 安装失败: {result.stderr[:500]}")
            return False

        # TODO: 解析 PyPI 包的元数据
        info = PluginInfo(
            name=package_name,
            source=PluginSource.PYPI,
            pypi_name=package_name,
        )

        self._plugins[package_name] = info
        self._save_index()
        logger.info(f"PyPI 插件安装成功: {package_name}")
        return True

    def _parse_plugin_metadata(self, plugin_dir: Path, name: str, repo_url: str) -> PluginInfo:
        """
        解析插件元数据

        尝试从以下位置读取元数据：
        1. pyproject.toml
        2. setup.py / setup.cfg
        3. README.md
        4. 插件特有的 manifest.json

        Args:
            plugin_dir: 插件目录
            name: 插件名称
            repo_url: 仓库 URL

        Returns:
            插件信息
        """
        info = PluginInfo(
            name=name,
            source=PluginSource.GITHUB,
            repo_url=repo_url,
            directory=str(plugin_dir),
        )

        # 尝试读取 pyproject.toml
        pyproject = plugin_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib  # Python 3.11+
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                project = data.get("project", {})
                info.version = project.get("version", "")
                info.description = project.get("description", "")
                info.author = project.get("authors", [{}])[0].get("name", "")
                info.requirements = project.get("dependencies", [])
            except Exception:
                pass

        # 尝试读取 requirements.txt
        req_file = plugin_dir / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    info.requirements = [
                        line.strip() for line in f
                        if line.strip() and not line.startswith("#")
                    ]
            except Exception:
                pass

        return info

    def update_plugin(self, name: str) -> bool:
        """更新单个插件"""
        plugin = self._plugins.get(name)
        if plugin is None or plugin.source != PluginSource.GITHUB:
            return False

        plugin_dir = Path(plugin.directory)
        if not plugin_dir.exists():
            return False

        logger.info(f"正在更新插件: {name}")
        result = subprocess.run(
            ["git", "-C", str(plugin_dir), "pull"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            logger.info(f"插件更新成功: {name}")
            return True
        else:
            logger.error(f"插件更新失败: {result.stderr[:500]}")
            return False

    def update_all_plugins(self) -> Dict[str, bool]:
        """更新所有已安装的插件"""
        results = {}
        for name in self._plugins:
            if self._plugins[name].source == PluginSource.GITHUB:
                results[name] = self.update_plugin(name)
        return results

    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False
        plugin.enabled = False
        plugin.status = PluginStatus.INACTIVE
        self._save_index()
        return True

    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False
        plugin.enabled = True
        plugin.status = PluginStatus.ACTIVE
        self._save_index()
        return True

    def remove_plugin(self, name: str) -> bool:
        """移除插件"""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False

        plugin_dir = Path(plugin.directory)
        if plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin_dir, ignore_errors=True)

        del self._plugins[name]
        self._save_index()
        logger.info(f"插件已移除: {name}")
        return True

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugins.get(name)

    def get_all_plugins(self) -> List[PluginInfo]:
        """获取所有插件"""
        return list(self._plugins.values())

    def get_enabled_plugins(self) -> List[PluginInfo]:
        """获取已启用的插件"""
        return [p for p in self._plugins.values() if p.enabled]

    def check_updates(self) -> List[str]:
        """
        检查所有 GitHub 插件的更新

        Returns:
            有更新的插件名称列表
        """
        outdated = []
        for name, plugin in self._plugins.items():
            if plugin.source == PluginSource.GITHUB and plugin.repo_url:
                try:
                    result = subprocess.run(
                        ["git", "-C", plugin.directory, "fetch", "origin"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        # 比较本地和远程分支
                        fetch_result = subprocess.run(
                            ["git", "-C", plugin.directory, "rev-parse",
                             "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, timeout=10
                        )
                        current_branch = fetch_result.stdout.strip()

                        hash_result = subprocess.run(
                            ["git", "-C", plugin.directory, "rev-parse",
                             f"origin/{current_branch}"],
                            capture_output=True, text=True, timeout=10
                        )
                        remote_hash = hash_result.stdout.strip()

                        local_hash_result = subprocess.run(
                            ["git", "-C", plugin.directory, "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=10
                        )
                        local_hash = local_hash_result.stdout.strip()

                        if remote_hash and local_hash and remote_hash != local_hash:
                            outdated.append(name)
                            plugin.status = PluginStatus.OUTDATED
                except Exception as e:
                    logger.debug(f"检查 {name} 更新失败: {e}")

        if outdated:
            self._save_index()
        return outdated
