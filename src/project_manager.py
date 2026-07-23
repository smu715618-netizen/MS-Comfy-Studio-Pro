"""Project Manager — 项目管理系统

管理用户的修图项目：
- 保存/恢复项目状态（图片、工作流、参数、模型引用）
- 版本历史（每次保存自动生成快照）
- 导出为工程文件/原始图片/PDF等
- 导入其他项目

设计原则：
- 不保存任何大型模型数据（只保存引用路径）
- 项目文件紧凑，便于共享和备份
- 支持摄影/电商/设计的真实工作流场景
"""

import os
import json
import shutil
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger

logger = get_logger("project")


@dataclass
class ProjectMetadata:
    """项目元数据"""
    name: str = ""
    description: str = ""
    created_at: str = ""
    modified_at: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = "general"          # portrait/product/editing/etc.
    version: str = "1.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMetadata":
        return cls(**data)


@dataclass
class ProjectSnapshot:
    """项目快照（某个时间点的完整状态）"""
    snapshot_id: str                     # UUID
    timestamp: str                      # ISO format
    model_checkpoint: str = ""          # 引用而非实际数据
    lora_files: List[str] = field(default_factory=list)
    workflow_json: Dict[str, Any] = field(default_factory=dict)  # ComfyUI prompt
    parameters: Dict[str, Any] = field(default_factory=dict)     # 所有可调参数
    input_images: List[str] = field(default_factory=list)        # 输入图片路径
    output_images: List[str] = field(default_factory=list)       # 输出图片路径
    notes: str = ""                     # 用户注释

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectSnapshot":
        return cls(**data)


class Project:
    """单个项目管理类"""

    def __init__(self, project_dir: str):
        self._project_dir = Path(project_dir)
        self._project_dir.mkdir(parents=True, exist_ok=True)
        self._input_dir = self._project_dir / "input"
        self._output_dir = self._project_dir / "output"
        self._snapshots_dir = self._project_dir / "snapshots"
        self._cache_dir = self._project_dir / "cache"

        for d in [self._input_dir, self._output_dir, self._snapshots_dir, self._cache_dir]:
            d.mkdir(exist_ok=True)

        self._metadata_file = self._project_dir / "metadata.json"
        self._history_file = self._project_dir / "history.json"

        self._metadata = self._load_metadata()
        self._history: List[Dict] = self._load_history()

    def _load_metadata(self) -> ProjectMetadata:
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    return ProjectMetadata.from_dict(json.load(f))
            except Exception as e:
                logger.warning(f"加载项目元数据失败: {e}")
        now = datetime.now().isoformat()
        return ProjectMetadata(name=self._project_dir.name, created_at=now, modified_at=now)

    def _save_metadata(self):
        self._metadata.modified_at = datetime.now().isoformat()
        with open(self._metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self._metadata.to_dict(), f, indent=2, ensure_ascii=False)

    def _load_history(self) -> List[Dict]:
        if self._history_file.exists():
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self):
        with open(self._history_file, 'w', encoding='utf-8') as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)

    # ---- 公开 API ----

    @property
    def metadata(self) -> ProjectMetadata:
        return self._metadata

    @property
    def project_dir(self) -> Path:
        return self._project_dir

    @property
    def input_dir(self) -> Path:
        return self._input_dir

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def save(self, workflow: Optional[Dict] = None, parameters: Optional[Dict] = None,
             input_images: Optional[List[str]] = None, output_images: Optional[List[str]] = None,
             notes: str = "") -> str:
        """
        保存当前项目状态为一个快照

        Args:
            workflow: ComfyUI prompt JSON
            parameters: 调优参数
            input_images: 输入图片文件列表
            output_images: 输出图片文件列表
            notes: 用户备注

        Returns:
            snapshot_id
        """
        from uuid import uuid4
        sid = str(uuid4())[:8]
        snap = ProjectSnapshot(
            snapshot_id=sid,
            timestamp=datetime.now().isoformat(),
            model_checkpoint="",  # 由 AI capability 层设置
            lora_files=[],
            workflow_json=workflow or {},
            parameters=parameters or {},
            input_images=input_images or [],
            output_images=output_images or [],
            notes=notes,
        )
        # 持久化
        snap_file = self._snapshots_dir / f"{sid}.json"
        with open(snap_file, 'w', encoding='utf-8') as f:
            json.dump(snap.to_dict(), f, indent=2, ensure_ascii=False)
        self._history.append({
            "snapshot_id": sid,
            "timestamp": snap.timestamp,
            "notes": notes,
        })
        self._save_history()
        logger.info(f"项目快照已保存: {sid}")
        return sid

    def load_snapshot(self, snapshot_id: str) -> Optional[ProjectSnapshot]:
        """加载指定快照"""
        snap_file = self._snapshots_dir / f"{snapshot_id}.json"
        if not snap_file.exists():
            return None
        try:
            with open(snap_file, 'r', encoding='utf-8') as f:
                return ProjectSnapshot.from_dict(json.load(f))
        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return None

    def delete_snapshot(self, snapshot_id: str) -> bool:
        snap_file = self._snapshots_dir / f"{snapshot_id}.json"
        if snap_file.exists():
            snap_file.unlink()
            self._history = [h for h in self._history if h.get('snapshot_id') != snapshot_id]
            self._save_history()
            return True
        return False

    def copy_to(self, dest_dir: str) -> bool:
        """复制整个项目到目标目录"""
        dest = Path(dest_dir) / self._metadata.name
        try:
            if dest.exists():
                logger.warning(f"目标路径已存在: {dest}")
                return False
            shutil.copytree(self._project_dir, dest)
            logger.info(f"项目已复制到: {dest}")
            return True
        except Exception as e:
            logger.error(f"复制项目失败: {e}")
            return False

    def get_history(self) -> List[Dict]:
        return list(self._history)


class ProjectManager:
    """
    项目管理中心 — 管理所有用户项目

    功能：
    - 创建新项目
    - 打开/关闭项目
    - 保存/恢复
    - 删除项目
    - 列出所有项目
    """

    def __init__(self, projects_dir: Optional[str] = None):
        if projects_dir is None:
            projects_dir = str(_project_root / "data" / "projects")
        self._projects_dir = Path(projects_dir)
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._current: Optional[Project] = None
        self._project_cache: Dict[str, Project] = {}  # name -> Project

    @property
    def current_project(self) -> Optional[Project]:
        return self._current

    def create_new(self, name: str = "", category: str = "general",
                   author: str = "") -> Optional[Project]:
        if not name:
            name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dir_path = self._projects_dir / name
        if dir_path.exists():
            logger.warning(f"项目已存在: {name}")
            return None
        proj = Project(str(dir_path))
        proj._metadata.category = category
        proj._metadata.author = author
        proj._metadata.name = name
        proj._save_metadata()
        self._project_cache[name] = proj
        logger.info(f"新项目已创建: {name}")
        return proj

    def open(self, name: str) -> Optional[Project]:
        dir_path = self._projects_dir / name
        if not dir_path.exists():
            logger.warning(f"项目不存在: {name}")
            return None
        if name not in self._project_cache:
            self._project_cache[name] = Project(str(dir_path))
        self._current = self._project_cache[name]
        return self._current

    def close(self):
        self._current = None

    def delete(self, name: str) -> bool:
        proj = self._project_cache.pop(name, None)
        if proj:
            shutil.rmtree(proj.project_dir, ignore_errors=True)
            logger.info(f"项目已删除: {name}")
            return True
        return False

    def get_all_projects(self) -> List[Dict[str, Any]]:
        result = []
        for name in sorted(os.listdir(self._projects_dir)):
            pdir = self._projects_dir / name
            meta_file = pdir / "metadata.json"
            hist_file = pdir / "history.json"
            info = {"name": name, "exists": pdir.is_dir()}
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        md = json.load(f)
                    info.update(md)
                except Exception:
                    pass
            if hist_file.exists():
                try:
                    with open(hist_file, 'r', encoding='utf-8') as f:
                        info["snapshot_count"] = len(json.load(f))
                except Exception:
                    pass
            result.append(info)
        return result

    def get_or_create(self, name: str) -> Optional[Project]:
        if name in self._project_cache:
            return self._project_cache[name]
        proj = self.open(name)
        if proj is None:
            return self.create_new(name)
        return proj
