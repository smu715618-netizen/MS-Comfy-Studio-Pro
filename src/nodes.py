"""
节点管理框架

管理 ComfyUI 节点的三种来源：
1. 内置节点 (Built-in) - ComfyUI 自带的核心节点
2. 社区节点 (Community) - 通过 git clone 安装的第三方节点
3. 自定义节点 (Custom) - 用户本地开发的节点

支持操作：
- 安装 / 卸载 / 更新节点
- 节点兼容性检查
- 节点启用 / 禁用
- 节点元数据管理
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

logger = get_logger("nodes")


class NodeSource(Enum):
    """节点来源"""
    BUILTIN = "builtin"       # ComfyUI 内置
    COMMUNITY = "community"   # 社区安装 (git)
    CUSTOM = "custom"         # 用户自定义


class NodeStatus(Enum):
    """节点状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"


@dataclass
class NodeInfo:
    """节点信息"""
    name: str                          # 节点名称
    source: NodeSource                 # 来源
    status: NodeStatus = NodeStatus.ENABLED
    version: str = ""                  # 版本
    description: str = ""              # 描述
    author: str = ""                   # 作者
    requirements: List[str] = field(default_factory=list)  # 依赖
    compatible_gpus: List[str] = field(default_factory=lambda: ["all"])  # 兼容 GPU
    directory: str = ""                # 目录路径

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NodeInfo":
        data = data.copy()
        if "source" in data:
            data["source"] = NodeSource(data["source"])
        if "status" in data:
            data["status"] = NodeStatus(data["status"])
        return cls(**data)


class NodeManager:
    """
    节点管理器

    管理 ComfyUI 的所有节点，包括内置、社区和自定义节点。
    """

    def __init__(self, comfyui_dir: Optional[str] = None):
        """
        初始化节点管理器

        Args:
            comfyui_dir: ComfyUI 安装目录
        """
        if comfyui_dir is None:
            comfyui_dir = str(Path(__file__).parent.parent / "comfyui")

        self._comfyui_dir = Path(comfyui_dir)
        self._custom_nodes_dir = self._comfyui_dir / "custom_nodes"
        self._index_file = Path(__file__).parent.parent / "data" / "nodes" / "index.json"

        # 节点索引
        self._nodes: Dict[str, NodeInfo] = {}

        # 确保目录存在
        self._custom_nodes_dir.mkdir(parents=True, exist_ok=True)
        self._index_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载索引
        self._load_index()
        # 扫描节点
        self._scan_nodes()

    def _load_index(self):
        """加载节点索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, info in data.items():
                    self._nodes[name] = NodeInfo.from_dict(info)
            except Exception as e:
                logger.error(f"加载节点索引失败: {e}")

    def _save_index(self):
        """保存节点索引"""
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {name: info.to_dict() for name, info in self._nodes.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"保存节点索引失败: {e}")

    def _scan_nodes(self):
        """扫描已安装的节点"""
        # 扫描 custom_nodes 目录
        if self._custom_nodes_dir.exists():
            for dir_path in self._custom_nodes_dir.iterdir():
                if dir_path.is_dir() and not dir_path.name.startswith("."):
                    name = dir_path.name
                    if name not in self._nodes:
                        self._nodes[name] = NodeInfo(
                            name=name,
                            source=NodeSource.COMMUNITY,
                            status=NodeStatus.ENABLED,
                            directory=str(dir_path),
                        )

        # 扫描内置节点（ComfyUI/web 和 ComfyUI/nodes）
        builtin_nodes_dir = self._comfyui_dir / "nodes"
        if builtin_nodes_dir.exists():
            # 内置节点通常不需要单独管理
            logger.debug("内置节点目录存在")

        self._save_index()

    def install_from_git(self, repo_url: str, node_name: Optional[str] = None) -> bool:
        """
        通过 Git 安装社区节点

        Args:
            repo_url: Git 仓库 URL
            node_name: 节点名称（自动从 URL 推断）

        Returns:
            是否成功
        """
        if node_name is None:
            node_name = repo_url.rstrip("/").split("/")[-1]

        target_dir = self._custom_nodes_dir / node_name

        if target_dir.exists():
            logger.warning(f"节点已存在: {node_name}")
            return False

        logger.info(f"正在安装节点: {node_name} ({repo_url})")

        result = subprocess.run(
            ["git", "clone", repo_url, str(target_dir)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.error(f"安装失败: {result.stderr[:500]}")
            return False

        # 安装节点依赖
        requirements_file = target_dir / "requirements.txt"
        if requirements_file.exists():
            logger.info(f"正在安装 {node_name} 的依赖...")
            subprocess.run(
                [str(Path(__file__).parent.parent / "venv" / "Scripts" / "python.exe"),
                 "-m", "pip", "install", "-r", str(requirements_file)],
                capture_output=True, text=True
            )

        self._nodes[node_name] = NodeInfo(
            name=node_name,
            source=NodeSource.COMMUNITY,
            status=NodeStatus.ENABLED,
            directory=str(target_dir),
        )
        self._save_index()
        logger.info(f"节点安装成功: {node_name}")
        return True

    def update_node(self, name: str) -> bool:
        """
        更新单个节点

        Args:
            name: 节点名称

        Returns:
            是否成功
        """
        node = self._nodes.get(name)
        if node is None or node.source != NodeSource.COMMUNITY:
            return False

        node_dir = Path(node.directory)
        if not node_dir.exists():
            return False

        logger.info(f"正在更新节点: {name}")
        result = subprocess.run(
            ["git", "-C", str(node_dir), "pull"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            logger.info(f"节点更新成功: {name}")
            return True
        else:
            logger.error(f"节点更新失败: {result.stderr[:500]}")
            return False

    def update_all_nodes(self) -> Dict[str, bool]:
        """
        更新所有已安装的社区节点

        Returns:
            {节点名称: 是否成功}
        """
        results = {}
        for name, node in self._nodes.items():
            if node.source == NodeSource.COMMUNITY:
                results[name] = self.update_node(name)
        return results

    def disable_node(self, name: str) -> bool:
        """禁用节点（通过创建 .disabled 文件）"""
        node = self._nodes.get(name)
        if node is None:
            return False

        node_dir = Path(node.directory)
        disabled_file = node_dir / ".disabled"
        disabled_file.touch()

        if name in self._nodes:
            self._nodes[name].status = NodeStatus.DISABLED
            self._save_index()
        return True

    def enable_node(self, name: str) -> bool:
        """启用节点（删除 .disabled 文件）"""
        node = self._nodes.get(name)
        if node is None:
            return False

        disabled_file = Path(node.directory) / ".disabled"
        if disabled_file.exists():
            disabled_file.unlink()

        if name in self._nodes:
            self._nodes[name].status = NodeStatus.ENABLED
            self._save_index()
        return True

    def remove_node(self, name: str) -> bool:
        """移除节点"""
        node = self._nodes.get(name)
        if node is None:
            return False

        node_dir = Path(node.directory)
        if node_dir.exists():
            import shutil
            shutil.rmtree(node_dir, ignore_errors=True)

        del self._nodes[name]
        self._save_index()
        logger.info(f"节点已移除: {name}")
        return True

    def get_node(self, name: str) -> Optional[NodeInfo]:
        """获取节点信息"""
        return self._nodes.get(name)

    def get_all_nodes(self) -> List[NodeInfo]:
        """获取所有节点"""
        return list(self._nodes.values())

    def get_nodes_by_source(self, source: NodeSource) -> List[NodeInfo]:
        """按来源获取节点"""
        return [n for n in self._nodes.values() if n.source == source]

    def get_enabled_nodes(self) -> List[NodeInfo]:
        """获取所有已启用的节点"""
        return [n for n in self._nodes.values() if n.status == NodeStatus.ENABLED]

    def get_compatible_nodes(self, gpu_type: str = "intel_xpu") -> List[NodeInfo]:
        """
        获取与指定 GPU 类型兼容的节点

        Args:
            gpu_type: GPU 类型标识

        Returns:
            兼容节点列表
        """
        compatible = []
        for node in self._nodes.values():
            if node.source == NodeSource.BUILTIN:
                compatible.append(node)
                continue
            if "all" in node.compatible_gpus:
                compatible.append(node)
            elif gpu_type in node.compatible_gpus:
                compatible.append(node)
        return compatible
