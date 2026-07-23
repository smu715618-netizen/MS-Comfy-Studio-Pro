"""
Node Center Foundation (节点管理中心)

管理所有 AI 节点的完整生命周期：
- 节点扫描（内置/社区/自定义）
- 节点安装/卸载/更新
- 节点启用/禁用
- 版本检测
- 依赖检测与自动修复
- 节点仓库接口（预留）

产品定位：Professional AI Photo Editing Studio
AI 只是能力层，ComfyUI 仅是底层执行引擎。
所有底层实现对用户隐藏。
"""

import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
import time

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger
from src.config_manager import ConfigManager

logger = get_logger("nodecenter")


# ================================================================
# 枚举和数据类
# ================================================================

class NodeType(Enum):
    """节点分类"""
    BUILTIN = "builtin"       # ComfyUI 内置核心节点
    COMMUNITY = "community"   # 社区节点（git 安装）
    CUSTOM = "custom"         # 用户自定义节点


class NodeStatus(Enum):
    """节点状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    OUTDATED = "outdated"


class InstallSource(Enum):
    """节点来源类型"""
    GITHUB = "github"
    GITLAB = "gitlab"
    ZIP_URL = "zip_url"
    LOCAL_FILE = "local_file"
    ENTERPRISE = "enterprise"


@dataclass
class NodeDependency:
    """节点依赖信息"""
    package_name: str
    version_spec: str = ""      # 如 "==1.0.0", ">=2.0"
    required: bool = True       # 是否必需
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "version_spec": self.version_spec,
            "required": self.required,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NodeDependency":
        return cls(**data)


@dataclass
class NodeInfo:
    """节点元数据（完整的节点信息）"""
    name: str                              # 节点标识名
    display_name: str = ""                 # 显示名称
    node_type: NodeType = NodeType.COMMUNITY
    source: InstallSource = InstallSource.GITHUB
    status: NodeStatus = NodeStatus.ENABLED
    version: str = ""                      # 当前版本
    latest_version: str = ""               # 最新版本（用于检测更新）
    description: str = ""                  # 描述
    author: str = ""                       # 作者/维护者
    homepage: str = ""                     # 主页/GitHub仓库
    directory: str = ""                    # 本地目录路径
    requirements: List[NodeDependency] = field(default_factory=list)  # 依赖包
    compatible_gpus: List[str] = field(default_factory=lambda: ["all"])  # 兼容GPU
    min_comfyui_version: str = ""          # 最低ComfyUI版本要求
    tags: List[str] = field(default_factory=list)  # 标签

    # 运行时信息
    last_checked: str = ""                 # 最后检查更新时间
    error_message: str = ""                # 错误信息
    installed_at: str = ""                 # 安装时间
    updated_at: str = ""                   # 更新时间

    def is_available(self) -> bool:
        """节点是否可用"""
        return self.status == NodeStatus.ENABLED

    def needs_update(self) -> bool:
        """是否需要更新"""
        if not self.version or not self.latest_version:
            return False
        try:
            return self._compare_versions(self.version, self.latest_version) < 0
        except Exception:
            return False

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号: -1=v1<v2, 0=v1==v2, 1=v1>v2"""
        p1 = [int(x) for x in v1.replace("-", ".").split(".") if x.isdigit()]
        p2 = [int(x) for x in v2.replace("-", ".").split(".") if x.isdigit()]
        if not p1 and not p2: return 0
        if not p1: return -1
        if not p2: return 1
        for a, b in zip(p1, p2):
            if a < b: return -1
            if a > b: return 1
        return len(p1) - len(p2)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["node_type"] = self.node_type.value
        d["source"] = self.source.value
        d["status"] = self.status.value
        d["requirements"] = [r.to_dict() if isinstance(r, NodeDependency) else r for r in self.requirements]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NodeInfo":
        data = data.copy()
        for key, enum_cls in [("node_type", NodeType), ("source", InstallSource), ("status", NodeStatus)]:
            if key in data and isinstance(data[key], str):
                data[key] = enum_cls(data[key])
        deps = data.get("requirements", [])
        data["requirements"] = [NodeDependency.from_dict(d) if isinstance(d, dict) else d for d in deps]
        return cls(**data)


# ================================================================
# 节点仓库接口
# ================================================================

class NodeRegistryAPI:
    """
    节点仓库接口（预留）

    定义统一的仓库查询接口。
    目前仅保留接口，后续阶段接入：
    - 官方节点市场 API
    - GitHub 搜索
    - Zip 本地安装
    - 企业内部仓库
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1小时缓存

    def search_nodes(self, query: str, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索节点（预留接口）

        Args:
            query: 搜索关键词
            source: 仓库类型（github/huggingface/custom）

        Returns:
            匹配节点列表（含name/description/version等）
        """
        # TODO: 连接官方仓库 API
        logger.info(f"搜索节点: '{query}' (预留接口)")
        return []

    def get_node_info(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        获取节点仓库信息

        Args:
            repo_url: GitHub 或其他仓库 URL

        Returns:
            包含名称、版本、描述、要求的字典
        """
        # TODO: 解析远程仓库的 manifest.json / package.json / README
        logger.info(f"获取节点信息: '{repo_url}' (预留接口)")
        return None

    def list_all_nodes(self) -> List[Dict[str, Any]]:
        """列出所有可安装的节点（预留接口）"""
        return []

    def check_available_updates(self) -> List[Dict[str, str]]:
        """检查哪些已安装节点有更新（预留接口）"""
        return []


# ================================================================
# 节点扫描器
# ================================================================

class NodeScanner:
    """
    节点扫描器

    扫描并发现系统中所有已安装的节点：
    - 内置节点（ComfyUI/nodes 等）
    - 社区节点（comfyui/custom_nodes/*/）
    - 自定义节点
    """

    def __init__(self, comfyui_dir: Path):
        self._comfyui_dir = comfyui_dir
        self._custom_nodes_dir = comfyui_dir / "custom_nodes"

    def scan_all(self) -> List[NodeInfo]:
        """扫描所有节点"""
        nodes = []
        nodes.extend(self._scan_builtin())
        nodes.extend(self._scan_community())
        nodes.extend(self._scan_custom())
        return nodes

    def _scan_builtin(self) -> List[NodeInfo]:
        """扫描 ComfyUI 内置节点"""
        nodes = []
        builtin_dirs = [
            self._comfyui_dir / "nodes",
            self._comfyui_dir / "comfy_extras",
            self._comfyui_dir,  # 根目录的 nodes.py
        ]
        for d in builtin_dirs:
            if d.exists():
                nodes.append(NodeInfo(
                    name=d.name,
                    display_name=f"ComfyUI 内置 ({d.name})",
                    node_type=NodeType.BUILTIN,
                    source=InstallSource.ENTERPRISE,
                    directory=str(d),
                    author="ComfyUI Team",
                    description="ComfyUI 内置核心节点",
                ))
        return nodes

    def _scan_community(self) -> List[NodeInfo]:
        """扫描 custom_nodes 下的社区节点"""
        nodes = []
        if not self._custom_nodes_dir.exists():
            return nodes

        for entry in sorted(self._custom_nodes_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith('.'):
                continue
            # 检查是否被禁用
            status = NodeStatus.DISABLED if (entry / ".disabled").exists() else NodeStatus.ENABLED

            # 尝试从 repo 获取版本
            version = ""
            git_dir = entry / ".git"
            if git_dir.exists():
                try:
                    result = subprocess.run(
                        ["git", "-C", str(entry), "describe", "--tags", "--always"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                except Exception:
                    pass

            nodes.append(NodeInfo(
                name=entry.name,
                display_name=entry.name,
                node_type=NodeType.COMMUNITY,
                source=InstallSource.GITHUB,
                status=status,
                version=version,
                directory=str(entry),
                installed_at=datetime.now().isoformat(),
            ))

        return nodes

    def _scan_custom(self) -> List[NodeInfo]:
        """扫描用户自定义节点（预留）"""
        # TODO: 扫描用户指定目录
        return []


# ================================================================
# 依赖管理器
# ================================================================

class DependencyChecker:
    """
    节点依赖检查器

    检测节点所需的 Python 包是否已安装。
    支持自动安装和冲突解决。
    """

    def __init__(self, comfyui_dir: Path):
        self._comfyui_dir = comfyui_dir
        self._venv_python = None  # 在需要时懒加载

    def check_requirements(self, requirements: List[NodeDependency]) -> Dict[str, str]:
        """
        检查依赖是否满足

        Returns:
            {包名: "ok"|"missing"|"conflict"}
        """
        results = {}
        installed = self._get_installed_packages()

        for req in requirements:
            pkg = req.package_name.lower().replace("_", "-")
            if pkg in installed:
                results[pkg] = "ok"
            elif not req.required:
                results[pkg] = "optional_missing"
            else:
                results[pkg] = "missing"
        return results

    def install_requirements(self, requirements: List[NodeDependency]) -> Dict[str, bool]:
        """
        安装缺失的依赖

        Returns:
            {包名: success}
        """
        # TODO: 集成 pip install
        results = {}
        for req in requirements:
            results[req.package_name] = False  # 占位
        return results

    def auto_fix_dependencies(self, node_name: str, requirements: List[NodeDependency]) -> List[str]:
        """
        自动修复依赖问题

        Returns:
            操作记录日志
        """
        issues = []
        missing = [r for r in requirements if r.required]
        if missing:
            issues.append(f"{node_name}: 发现 {len(missing)} 个缺失依赖")
            # TODO: 调用 install_requirements
        return issues

    def _get_installed_packages(self) -> Set[str]:
        """获取已安装的包名列表"""
        return set()  # 占位

    def detect_conflicts(self, new_reqs: List[NodeDependency], existing_pkgs: Set[str]) -> List[str]:
        """检测潜在冲突"""
        conflicts = []
        for req in new_reqs:
            pkg = req.package_name.lower()
            if pkg in existing_pkgs:
                # 检查版本兼容性
                if req.version_spec:
                    conflicts.append(f"版本冲突: {pkg} {req.version_spec}")
        return conflicts


# ================================================================
# 主节点管理器
# ================================================================

class NodeManager:
    """
    节点管理器（企业级）

    统一管理所有 AI 节点的：
    - 生命周期（安装/卸载/启用/禁用/更新）
    - 状态追踪（健康检查）
    - 依赖管理
    - 版本检测
    - 仓库对接（预留）
    """

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = str(_project_root)
        self._project_root = Path(project_root)
        self._config = ConfigManager()

        # ComfyUI 路径
        comfyui_path_str = self._config.get("paths.comfyui_dir", "comfyui")
        self._comfyui_dir = self._project_root / comfyui_path_str
        custom_dir = self._comfyui_dir / "custom_nodes"
        custom_dir.mkdir(parents=True, exist_ok=True)

        # 索引
        self._index_file = self._project_root / "data" / "nodes" / "index.json"
        self._index_file.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: Dict[str, NodeInfo] = {}

        # 组件
        self._scanner = NodeScanner(self._comfyui_dir)
        self._dep_checker = DependencyChecker(self._comfyui_dir)
        self._registry = NodeRegistryAPI()

        # 回调
        self._on_node_change_callbacks: List[Callable] = []

        # 加载索引 + 扫描
        self._load_index()
        self._scan_and_index()

    # ---- 生命周期 ----

    def install_from_git(self, repo_url: str) -> Optional[str]:
        """
        通过 Git 安装节点

        Args:
            repo_url: GitHub/GitLab 仓库地址

        Returns:
            节点名称，或失败时返回 None
        """
        # 推断节点名
        node_name = repo_url.rstrip("/").split("/")[-1]

        target_dir = self._comfyui_dir / "custom_nodes" / node_name
        if target_dir.exists():
            logger.warning(f"节点已存在: {node_name}")
            return None

        logger.info(f"安装节点: {node_name} ({repo_url})")
        result = subprocess.run(
            ["git", "clone", repo_url, str(target_dir)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            logger.error(f"克隆失败: {result.stderr[:500]}")
            return None

        # 提取 requirements.txt
        req_file = target_dir / "requirements.txt"
        if req_file.exists():
            with open(req_file, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
                # TODO: 解析版本约束

        self._add_node(NodeInfo(
            name=node_name,
            display_name=node_name,
            node_type=NodeType.COMMUNITY,
            source=InstallSource.GITHUB,
            directory=str(target_dir),
            homepage=repo_url,
            installed_at=datetime.now().isoformat(),
        ))
        logger.info(f"安装成功: {node_name}")
        return node_name

    def install_from_zip(self, zip_path: str, node_name: Optional[str] = None) -> bool:
        """从本地 Zip 文件安装（预留接口）"""
        logger.info(f"Zip 安装: {zip_path} (预留接口)")
        return False

    def install_from_local(self, dir_path: str) -> bool:
        """从本地目录安装为自定义节点"""
        d = Path(dir_path)
        if not d.is_dir():
            return False
        name = d.name
        self._add_node(NodeInfo(
            name=name,
            display_name=name,
            node_type=NodeType.CUSTOM,
            source=InstallSource.LOCAL_FILE,
            directory=str(d),
            installed_at=datetime.now().isoformat(),
        ))
        return True

    def uninstall(self, name: str) -> bool:
        """
        卸载节点

        删除节点文件并从索引中移除。
        """
        info = self._nodes.get(name)
        if not info:
            return False

        node_dir = Path(info.directory)
        if node_dir.exists():
            import shutil
            try:
                shutil.rmtree(node_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"卸载失败 ({name}): {e}")
                return False

        del self._nodes[name]
        self._save_index()
        logger.info(f"节点已卸载: {name}")
        return True

    # ---- 启用/禁用 ----

    def enable(self, name: str) -> bool:
        """启用节点"""
        info = self._nodes.get(name)
        if not info or info.status == NodeStatus.ENABLED:
            return False
        # 移除 .disabled 标记
        node_dir = Path(info.directory)
        disabled_file = node_dir / ".disabled"
        if disabled_file.exists():
            disabled_file.unlink()
        info.status = NodeStatus.ENABLED
        self._save_index()
        return True

    def disable(self, name: str) -> bool:
        """禁用节点"""
        info = self._nodes.get(name)
        if not info or info.status == NodeStatus.DISABLED:
            return False
        node_dir = Path(info.directory)
        (node_dir / ".disabled").touch()
        info.status = NodeStatus.DISABLED
        self._save_index()
        return True

    # ---- 更新 ----

    def update(self, name: str) -> bool:
        """
        更新单个节点
        """
        info = self._nodes.get(name)
        if not info or info.node_type != NodeType.COMMUNITY:
            return False

        node_dir = Path(info.directory)
        if not node_dir.exists():
            return False

        logger.info(f"更新节点: {name}")
        result = subprocess.run(
            ["git", "-C", str(node_dir), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            # 重新检查版本
            info.updated_at = datetime.now().isoformat()
            self._save_index()
            logger.info(f"更新成功: {name}")
            return True
        else:
            info.status = NodeStatus.ERROR
            info.error_message = result.stderr[:200]
            self._save_index()
            return False

    def update_all(self) -> Dict[str, bool]:
        """更新所有可更新的社区节点"""
        results = {}
        for name, info in list(self._nodes.items()):
            if info.node_type == NodeType.COMMUNITY:
                results[name] = self.update(name)
        return results

    # ---- 版本检测 ----

    def check_updates(self) -> Dict[str, str]:
        """
        检查所有节点版本是否有可用更新

        Returns:
            {节点名: "up-to-date"|"update-available"|"error"}
        """
        results = {}
        for name, info in self._nodes.items():
            if info.node_type != NodeType.COMMUNITY:
                results[name] = "skipped"
                continue
            # TODO: 实际检查远程版本
            results[name] = "up-to-date"  # 占位
        return results

    # ---- 依赖检测 ----

    def check_dependencies(self, name: str) -> Dict[str, str]:
        """
        检查单个节点的所有依赖状态

        Returns:
            {包名: "ok"|"missing"|"conflict"}
        """
        info = self._nodes.get(name)
        if not info:
            return {"_error": "节点不存在"}
        return self._dep_checker.check_requirements(info.requirements)

    def auto_fix(self, name: str) -> bool:
        """
        自动修复节点依赖问题

        先重新扫描依赖，然后自动安装缺失包。
        """
        info = self._nodes.get(name)
        if not info:
            return False
        issues = self._dep_checker.auto_fix_dependencies(name, info.requirements)
        return len(issues) == 0

    # ---- 信息查询 ----

    def get_node(self, name: str) -> Optional[NodeInfo]:
        return self._nodes.get(name)

    def get_all(self) -> List[NodeInfo]:
        return list(self._nodes.values())

    def get_by_type(self, node_type: NodeType) -> List[NodeInfo]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_enabled(self) -> List[NodeInfo]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.ENABLED]

    def get_disabled(self) -> List[NodeInfo]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.DISABLED]

    def get_with_update_available(self) -> List[str]:
        """获取有待更新版本的节点名称列表"""
        # TODO: 结合 check_updates 结果
        return []

    def get_summary(self) -> Dict[str, Any]:
        """获取节点管理摘要（供 Dashboard 显示）"""
        by_type = {}
        by_status = {"enabled": 0, "disabled": 0, "error": 0}
        for n in self._nodes.values():
            t = n.node_type.value
            by_type[t] = by_type.get(t, 0) + 1
            s = n.status.value
            if s == "enabled":
                by_status["enabled"] += 1
            elif s == "disabled":
                by_status["disabled"] += 1
            elif s == "error":
                by_status["error"] += 1
        return {
            "total": len(self._nodes),
            "by_type": by_type,
            "by_status": by_status,
        }

    # ---- 仓库接口 ----

    def registry_search(self, query: str) -> List[Dict[str, Any]]:
        """在节点仓库中搜索"""
        return self._registry.search_nodes(query)

    def registry_get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """获取仓库信息"""
        return self._registry.get_node_info(url)

    # ---- 内部方法 ----

    def _scan_and_index(self):
        """扫描并重建索引"""
        scanned = self._scanner.scan_all()
        for info in scanned:
            # 如果已有索引，合并元数据
            existing = self._nodes.get(info.name)
            if existing:
                if not info.version:
                    info.version = existing.version
                if not info.installed_at:
                    info.installed_at = existing.installed_at
            self._nodes[info.name] = info
        self._save_index()

    def _add_node(self, info: NodeInfo):
        """添加节点到索引"""
        self._nodes[info.name] = info
        self._save_index()

    def _load_index(self):
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, info_data in data.items():
                    self._nodes[name] = NodeInfo.from_dict(info_data)
            except Exception as e:
                logger.warning(f"加载节点索引失败: {e}")

    def _save_index(self):
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._nodes.items()},
                    f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"保存节点索引失败: {e}")


# ================================================================
# 全局单例
# ================================================================

_instance = None

def get_node_manager(project_root: Optional[str] = None) -> NodeManager:
    global _instance
    if _instance is None or project_root:
        _instance = NodeManager(project_root)
    return _instance
