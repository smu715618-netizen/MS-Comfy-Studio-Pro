"""
工作流管理框架

管理 ComfyUI 工作流的生命周期：
- 工作流模板（预设的常用工作流）
- 用户工作流（保存/导入/导出）
- 工作流分类与标签
- 工作流依赖检查（模型、节点）

工作流文件格式: ComfyUI JSON 格式 (workflow.json)
存储位置: data/workflows/{category}/{name}.json
"""

import os
import json
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.logger import get_logger
from src.models import ModelManager

logger = get_logger("workflows")


@dataclass
class WorkflowInfo:
    """工作流信息"""
    name: str                          # 工作流名称
    description: str = ""              # 描述
    category: str = "general"          # 分类
    tags: List[str] = field(default_factory=list)  # 标签
    requires_models: List[str] = field(default_factory=list)  # 需要的模型
    requires_nodes: List[str] = field(default_factory=list)   # 需要的节点
    input_schema: dict = field(default_factory=dict)  # 输入参数 schema
    output_schema: dict = field(default_factory=dict) # 输出参数 schema
    thumbnail: str = ""                # 缩略图路径
    created_at: str = ""               # 创建时间
    modified_at: str = ""              # 修改时间
    is_template: bool = False          # 是否为模板
    is_builtin: bool = False           # 是否为内置

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowInfo":
        return cls(**data)


class WorkflowManager:
    """
    工作流管理器

    管理工作流的存储、导入、导出和模板管理。
    """

    # 预置工作流分类
    CATEGORIES = {
        "portrait_retouch": "人像精修",
        "id_photo": "证件照",
        "upscale": "高清修复",
        "inpaint": "局部重绘",
        "background_remove": "背景移除",
        "photo_enlarge": "照片放大",
        "general": "通用",
    }

    def __init__(self, workflows_dir: Optional[str] = None):
        """
        初始化工作流管理器

        Args:
            workflows_dir: 工作流存储目录
        """
        if workflows_dir is None:
            workflows_dir = str(Path(__file__).parent.parent / "data" / "workflows")

        self._workflows_dir = Path(workflows_dir)
        self._templates_dir = self._workflows_dir / "templates"
        self._user_dir = self._workflows_dir / "user"
        self._builtin_dir = self._workflows_dir / "builtins"

        # 工作流索引: {workflow_name: WorkflowInfo}
        self._index: Dict[str, WorkflowInfo] = {}

        # 确保目录结构
        for cat in self.CATEGORIES:
            (self._user_dir / cat).mkdir(parents=True, exist_ok=True)
            (self._templates_dir / cat).mkdir(parents=True, exist_ok=True)
            (self._builtin_dir / cat).mkdir(parents=True, exist_ok=True)

        self._load_index()

    def _load_index(self):
        """加载工作流索引"""
        index_file = self._workflows_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, info in data.items():
                    self._index[name] = WorkflowInfo.from_dict(info)
            except Exception as e:
                logger.error(f"加载工作流索引失败: {e}")

    def _save_index(self):
        """保存工作流索引"""
        index_file = self._workflows_dir / "index.json"
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {name: info.to_dict() for name, info in self._index.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"保存工作流索引失败: {e}")

    def save_workflow(
        self,
        name: str,
        workflow_data: dict,
        category: str = "general",
        info: Optional[WorkflowInfo] = None,
    ) -> bool:
        """
        保存工作流

        Args:
            name: 工作流名称
            workflow_data: ComfyUI JSON 格式的工作流数据
            category: 分类
            info: 工作流元信息

        Returns:
            是否成功
        """
        if info is None:
            info = WorkflowInfo(name=name, category=category)

        now = datetime.now().isoformat()
        info.created_at = now
        info.modified_at = now

        # 确定保存路径
        save_dir = self._user_dir / category
        workflow_file = save_dir / f"{name}.json"

        try:
            with open(workflow_file, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)

            self._index[name] = info
            self._save_index()
            logger.info(f"工作流已保存: {name}")
            return True

        except Exception as e:
            logger.error(f"保存工作流失败: {e}")
            return False

    def load_workflow(self, name: str) -> Optional[dict]:
        """
        加载工作流数据

        Args:
            name: 工作流名称

        Returns:
            工作流 JSON 数据，或 None
        """
        info = self._index.get(name)
        if info is None:
            return None

        # 尝试从多个位置加载
        search_paths = [
            self._user_dir / info.category / f"{name}.json",
            self._templates_dir / info.category / f"{name}.json",
            self._builtin_dir / info.category / f"{name}.json",
        ]

        for path in search_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"加载工作流失败 {path}: {e}")
                    return None

        return None

    def import_workflow(self, file_path: str, category: str = "user") -> bool:
        """
        从文件导入工作流

        Args:
            file_path: 工作流 JSON 文件路径
            category: 导入到哪个分类

        Returns:
            是否成功
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 提取工作流名称
            name = Path(file_path).stem

            # 检查是否为有效的 ComfyUI 工作流
            if "nodes" not in data or "links" not in data:
                logger.warning(f"不是有效的 ComfyUI 工作流格式: {file_path}")
                return False

            return self.save_workflow(name, data, category)

        except Exception as e:
            logger.error(f"导入工作流失败: {e}")
            return False

    def export_workflow(self, name: str, output_path: str) -> bool:
        """
        导出工作流到文件

        Args:
            name: 工作流名称
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        workflow_data = self.load_workflow(name)
        if workflow_data is None:
            return False

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
            logger.info(f"工作流已导出: {name} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出工作流失败: {e}")
            return False

    def delete_workflow(self, name: str) -> bool:
        """删除工作流"""
        info = self._index.get(name)
        if info is None:
            return False

        workflow_file = self._user_dir / info.category / f"{name}.json"
        if workflow_file.exists():
            workflow_file.unlink()

        del self._index[name]
        self._save_index()
        logger.info(f"工作流已删除: {name}")
        return True

    def get_workflow(self, name: str) -> Optional[WorkflowInfo]:
        """获取工作流信息"""
        return self._index.get(name)

    def get_all_workflows(self) -> List[WorkflowInfo]:
        """获取所有工作流"""
        return list(self._index.values())

    def get_workflows_by_category(self, category: str) -> List[WorkflowInfo]:
        """按分类获取工作流"""
        return [w for w in self._index.values() if w.category == category]

    def get_templates(self) -> List[WorkflowInfo]:
        """获取所有模板工作流"""
        return [w for w in self._index.values() if w.is_template]

    def check_dependencies(self, name: str, model_mgr: Optional[ModelManager] = None) -> dict:
        """
        检查工作流依赖是否满足

        Args:
            name: 工作流名称
            model_mgr: 模型管理器（可选）

        Returns:
            依赖检查结果
        """
        info = self._index.get(name)
        if info is None:
            return {"valid": False, "error": "工作流不存在"}

        result = {
            "valid": True,
            "missing_models": [],
            "missing_nodes": [],
            "warnings": [],
        }

        # 检查模型依赖
        if model_mgr:
            for model_name in info.requires_models:
                if model_mgr.get_model(model_name) is None:
                    result["missing_models"].append(model_name)
                    result["valid"] = False

        # 检查节点依赖
        for node_name in info.requires_nodes:
            if node_name not in ("comfy-core",):  # 内置节点总是可用
                result["missing_nodes"].append(node_name)
                result["valid"] = False

        return result
