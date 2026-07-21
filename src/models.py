"""
模型管理框架

负责模型的生命周期管理：
- 模型分类（Checkpoint, VAE, CLIP, UNet, LoRA, ControlNet, Upscale, Embedding）
- 模型下载（支持断点续传、多线程）
- 模型验证（SHA256 校验）
- 模型元数据管理（JSON 索引）
- 模型存储管理（磁盘空间监控）

所有模型存储在 data/models/{type}/ 目录下。
模型索引存储在 data/models/index.json 文件中。
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Callable
from src.logger import get_logger
from src.config_manager import get_config

logger = get_logger("models")


class ModelType(Enum):
    """模型类型枚举"""
    CHECKPOINT = "checkpoints"
    VAE = "vae"
    CLIP = "clip"
    UNET = "unet"
    LORA = "lora"
    CONTROLNET = "controlnet"
    UPSCALE = "upscale"
    EMBEDDING = "embedding"

    @property
    def display_name(self) -> str:
        """显示名称（中文）"""
        names = {
            ModelType.CHECKPOINT: "Checkpoint",
            ModelType.VAE: "VAE",
            ModelType.CLIP: "CLIP",
            ModelType.UNET: "UNet",
            ModelType.LORA: "LoRA",
            ModelType.CONTROLNET: "ControlNet",
            ModelType.UPSCALE: "超分辨率模型",
            ModelType.EMBEDDING: "Embedding",
        }
        return names.get(self, self.value)


class ModelStatus(Enum):
    """模型状态枚举"""
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    MISSING = "missing"


@dataclass
class ModelMetadata:
    """模型元数据"""
    name: str                          # 模型名称
    model_type: ModelType              # 模型类型
    filename: str                      # 文件名
    file_size_bytes: int = 0           # 文件大小（字节）
    sha256_hash: str = ""              # SHA256 校验值
    status: ModelStatus = ModelStatus.AVAILABLE
    source: str = ""                   # 来源（HuggingFace / Civitai）
    source_url: str = ""               # 下载链接
    version: str = ""                  # 模型版本
    author: str = ""                   # 作者
    description: str = ""              # 描述
    tags: List[str] = field(default_factory=list)
    installed_at: str = ""             # 安装时间
    last_used: str = ""                # 最后使用时间

    def to_dict(self) -> dict:
        """序列化为字典"""
        d = asdict(self)
        d["model_type"] = self.model_type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetadata":
        """从字典反序列化"""
        data = data.copy()
        if "model_type" in data:
            data["model_type"] = ModelType(data["model_type"])
        if "status" in data:
            data["status"] = ModelStatus(data["status"])
        return cls(**data)


class ModelManager:
    """
    模型管理器

    管理所有模型的安装、下载、验证和索引。
    线程安全，支持并发下载。
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化模型管理器

        Args:
            data_dir: 数据根目录，默认为 data/
        """
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data")

        self._data_dir = Path(data_dir)
        self._models_dir = self._data_dir / "models"
        self._index_file = self._models_dir / "index.json"
        self._lock = threading.RLock()

        # 模型索引: {model_name: ModelMetadata}
        self._index: Dict[str, ModelMetadata] = {}

        # 下载回调
        self._download_callbacks: List[Callable] = []

        # 确保目录结构存在
        self._ensure_dirs()

        # 加载索引
        self._load_index()

    def _ensure_dirs(self):
        """确保模型目录结构存在"""
        for model_type in ModelType:
            type_dir = self._models_dir / model_type.value
            type_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self):
        """加载模型索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, meta in data.items():
                    self._index[name] = ModelMetadata.from_dict(meta)
                logger.info(f"已加载 {len(self._index)} 个模型索引")
            except Exception as e:
                logger.error(f"加载模型索引失败: {e}")
                self._index = {}
        else:
            logger.debug("模型索引不存在，将创建新索引")

    def _save_index(self):
        """保存模型索引到文件"""
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {name: meta.to_dict() for name, meta in self._index.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"保存模型索引失败: {e}")

    def add_model(self, metadata: ModelMetadata):
        """
        添加模型到索引

        Args:
            metadata: 模型元数据
        """
        with self._lock:
            self._index[metadata.name] = metadata
            self._save_index()
        logger.info(f"已添加模型: {metadata.name} ({metadata.model_type.value})")

    def remove_model(self, name: str) -> bool:
        """
        从索引中移除模型

        Args:
            name: 模型名称

        Returns:
            是否成功移除
        """
        with self._lock:
            if name in self._index:
                del self._index[name]
                self._save_index()
                logger.info(f"已移除模型: {name}")
                return True
        return False

    def get_model(self, name: str) -> Optional[ModelMetadata]:
        """
        获取模型元数据

        Args:
            name: 模型名称

        Returns:
            模型元数据，或 None
        """
        return self._index.get(name)

    def get_models_by_type(self, model_type: ModelType) -> List[ModelMetadata]:
        """
        按类型获取所有模型

        Args:
            model_type: 模型类型

        Returns:
            模型元数据列表
        """
        return [
            meta for meta in self._index.values()
            if meta.model_type == model_type
        ]

    def get_all_models(self) -> List[ModelMetadata]:
        """获取所有已注册模型"""
        return list(self._index.values())

    def get_model_path(self, name: str) -> Optional[Path]:
        """
        获取模型的完整文件路径

        Args:
            name: 模型名称

        Returns:
            文件路径，或 None
        """
        meta = self._index.get(name)
        if meta is None:
            return None
        type_dir = self._models_dir / meta.model_type.value
        return type_dir / meta.filename

    def register_model_file(self, filepath: Path, model_type: ModelType) -> Optional[ModelMetadata]:
        """
        扫描已有模型文件并注册到索引

        Args:
            filepath: 模型文件路径
            model_type: 模型类型

        Returns:
            创建的模型元数据，或 None
        """
        if not filepath.exists():
            return None

        name = filepath.stem
        metadata = ModelMetadata(
            name=name,
            model_type=model_type,
            filename=filepath.name,
            file_size_bytes=filepath.stat().st_size,
            installed_at=str(Path(filepath).stem),
            status=ModelStatus.AVAILABLE,
        )

        # 尝试计算 SHA256
        sha256 = self._calculate_sha256(filepath)
        if sha256:
            metadata.sha256_hash = sha256
            metadata.status = ModelStatus.VERIFIED

        self.add_model(metadata)
        return metadata

    def _calculate_sha256(self, filepath: Path, chunk_size: int = 8192) -> Optional[str]:
        """计算文件的 SHA256 哈希值"""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"计算 SHA256 失败: {e}")
            return None

    def verify_model(self, name: str) -> bool:
        """
        验证模型文件的完整性

        Args:
            name: 模型名称

        Returns:
            是否验证通过
        """
        meta = self._index.get(name)
        if meta is None:
            return False

        filepath = self.get_model_path(name)
        if filepath is None or not filepath.exists():
            meta.status = ModelStatus.MISSING
            return False

        # 重新计算 SHA256
        current_hash = self._calculate_sha256(filepath)
        if current_hash == meta.sha256_hash:
            meta.status = ModelStatus.VERIFIED
            return True
        else:
            meta.status = ModelStatus.CORRUPTED
            logger.warning(f"模型校验失败: {name}")
            return False

    def get_storage_usage(self) -> dict:
        """
        获取模型存储使用情况

        Returns:
            存储统计信息
        """
        total_size = 0
        by_type: Dict[str, int] = {}

        for model_type in ModelType:
            type_dir = self._models_dir / model_type.value
            type_size = 0
            if type_dir.exists():
                for f in type_dir.iterdir():
                    if f.is_file():
                        type_size += f.stat().st_size
            by_type[model_type.value] = type_size
            total_size += type_size

        return {
            "total_bytes": total_size,
            "total_mb": round(total_size / (1024 * 1024), 2),
            "total_gb": round(total_size / (1024 * 1024 * 1024), 3),
            "by_type": by_type,
            "model_count": len(self._index),
        }

    def on_download_progress(self, callback: Callable):
        """
        注册下载进度回调

        Args:
            callback: 回调函数 (model_name, downloaded_bytes, total_bytes) -> None
        """
        self._download_callbacks.append(callback)

    def _notify_progress(self, name: str, downloaded: int, total: int):
        """通知下载进度"""
        for cb in self._download_callbacks:
            try:
                cb(name, downloaded, total)
            except Exception as e:
                logger.error(f"下载进度回调失败: {e}")
