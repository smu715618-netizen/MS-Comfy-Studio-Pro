"""models.py — 模型管理系统

管理 ComfyUI 所有模型的生命周期：
- 模型分类 (Checkpoint/LoRA/VAE/ControlNet/Embedding等)
- 模型扫描与索引
- 模型信息读取
- 模型状态检测
- 下载框架（接口）

设计原则：
- 程序与模型彻底解耦：不内置任何大型模型
- 按需加载：不预装任何模型文件
- 配置驱动：所有目录通过 configs/models.yaml 管理
- 可扩展：新增模型类型只需在配置中添加，无需改代码
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger
from src.config_manager import ConfigManager

logger = get_logger("models")


# ================================================================
# 枚举和数据类
# ================================================================

class ModelType(Enum):
    """模型类型枚举（完全由 models.yaml 驱动扩展）"""
    CHECKPOINT = "checkpoints"
    LORA = "lora"
    VAE = "vae"
    CLIP = "clip"
    UNET = "unet"
    CONTROLNET = "controlnet"
    UPSCALE = "upscale"
    EMBEDDING = "embedding"
    IPADAPTER = "ipadapter"
    # 未来扩展预留
    TEXTUAL_INVERSION = "textual_inversion"

    @property
    def display_name(self) -> str:
        names = {
            ModelType.CHECKPOINT: "Checkpoint",
            ModelType.LORA: "LoRA",
            ModelType.VAE: "VAE",
            ModelType.CLIP: "CLIP",
            ModelType.UNET: "UNet",
            ModelType.CONTROLNET: "ControlNet",
            ModelType.UPSCALE: "超分辨率",
            ModelType.EMBEDDING: "Embedding",
            ModelType.IPADAPTER: "IPAdapter",
            ModelType.TEXTUAL_INVERSION: "Textual Inversion",
        }
        return names.get(self, self.value)

    @property
    def supported_formats(self) -> List[str]:
        formats = {
            ModelType.CHECKPOINT: [".safetensors", ".ckpt", ".bin"],
            ModelType.LORA: [".safetensors", ".ckpt"],
            ModelType.VAE: [".safetensors", ".ckpt"],
            ModelType.CLIP: [".safetensors", ".pt", ".bin"],
            ModelType.UNET: [".safetensors", ".bin"],
            ModelType.CONTROLNET: [".safetensors", ".pt"],
            ModelType.UPSCALE: [".safetensors", ".pt", ".onnx"],
            ModelType.EMBEDDING: [".safetensors", ".pt"],
            ModelType.IPADAPTER: [".safetensors", ".pt"],
            ModelType.TEXTUAL_INVERSION: [".safetensors", ".pt"],
        }
        return formats.get(self, [])


class ModelStatus(Enum):
    """模型状态"""
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    SYMLINK_ONLY = "symlink_only"  # 仅记录无实际文件


@dataclass
class ModelMetadata:
    """单个模型的元数据"""
    name: str                                    # 显示名称
    model_type: ModelType                        # 模型类型
    filename: str                                # 文件名
    file_path: str = ""                          # 完整路径
    file_size_bytes: int = 0                     # 文件大小
    sha256_hash: str = ""                        # SHA256校验值
    status: ModelStatus = ModelStatus.AVAILABLE
    source: str = ""                             # 来源（HuggingFace/Civitai）
    source_url: str = ""                         # 原始下载链接
    version: str = ""                            # 模型版本
    author: str = ""                             # 作者
    tags: List[str] = field(default_factory=list)
    created_at: str = ""                         # 创建时间
    installed_at: str = ""                       # 安装时间
    last_used: str = ""                          # 最后使用时间
    thumbnail: str = ""                          # 缩略图路径

    def to_dict(self) -> dict:
        d = asdict(self)
        d["model_type"] = self.model_type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetadata":
        data = data.copy()
        if "model_type" in data:
            data["model_type"] = ModelType(data["model_type"])
        if "status" in data:
            data["status"] = ModelStatus(data["status"])
        return cls(**data)


# ================================================================
# 模型扫描和索引核心
# ================================================================

class ModelScanner:
    """
    模型扫描器 — 扫描指定目录，发现并索引模型文件

    工作模式：
    - 递归扫描每个模型类型的子目录
    - 根据配置的文件格式过滤
    - 计算文件统计信息（大小、修改时间）
    - 可选SHA256校验
    """

    def __init__(self, model_dir: Path):
        self._model_dir = model_dir
        self._lock = threading.RLock()

    def scan_by_type(self, model_type: ModelType, recursive: bool = True) -> List[Path]:
        """
        按类型扫描模型文件

        Args:
            model_type: 模型类型
            recursive: 是否递归扫描子目录

        Returns:
            模型文件路径列表
        """
        subfolder = self._model_dir / model_type.value
        if not subfolder.exists():
            return []

        extensions = set()
        for fmt in model_type.supported_formats:
            extensions.add(fmt.lower())

        results = []
        if recursive:
            for ext in extensions:
                results.extend(subfolder.glob(f"**/*{ext}"))
        else:
            for ext in extensions:
                results.extend(subfolder.glob(f"*{ext}"))

        # 排除隐藏文件和缓存
        return [p for p in results if not p.name.startswith('.')]

    def scan_all_types(self, recursive: bool = True) -> Dict[str, List[Path]]:
        """
        扫描所有模型类型

        Returns:
            {类型名: [文件路径列表]}
        """
        result = {}
        for mt in ModelType:
            files = self.scan_by_type(mt, recursive)
            if files:
                result[mt.value] = files
        return result

    def get_directory_usage(self, model_type: Optional[ModelType] = None) -> Dict[str, Any]:
        """
        获取目录空间使用情况

        Args:
            model_type: 可选，只检查特定类型

        Returns:
            使用统计字典
        """
        total_size = 0
        file_count = 0
        by_type: Dict[str, int] = {}

        dirs_to_scan = [self._model_dir] if model_type is None else \
                       [self._model_dir / model_type.value]

        for dir_path in dirs_to_scan:
            if not dir_path.exists():
                continue
            for f in dir_path.rglob("*"):
                if f.is_file() and not f.name.startswith('.'):
                    try:
                        size = f.stat().st_size
                        total_size += size
                        file_count += 1
                        # 归类到最近一层目录
                        rel = f.relative_to(dir_path)
                        type_name = str(rel.parts[0]) if len(rel.parts) > 1 else "other"
                        by_type[type_name] = by_type.get(type_name, 0) + size
                    except OSError:
                        pass

        return {
            "total_bytes": total_size,
            "total_mb": round(total_size / (1024 * 1024), 2),
            "total_gb": round(total_size / (1024**3), 3),
            "file_count": file_count,
            "by_type": {k: round(v / (1024*1024), 2) for k, v in by_type.items()},
        }


# ================================================================
# 模型索引管理
# ================================================================

class ModelIndex:
    """
    模型索引管理器

    维护已安装模型的JSON索引。
    支持增删查改和持久化。
    """

    def __init__(self, index_file: Path):
        self._index_file = index_file
        self._index: Dict[str, ModelMetadata] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, meta in data.items():
                    self._index[name] = ModelMetadata.from_dict(meta)
            except Exception as e:
                logger.warning(f"加载模型索引失败: {e}，将创建新索引")
                self._index = {}

    def _save(self):
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {name: meta.to_dict() for name, meta in self._index.items()},
                    f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"保存模型索引失败: {e}")

    def add_or_update(self, metadata: ModelMetadata):
        """添加或更新模型索引"""
        with self._lock:
            self._index[metadata.name] = metadata
            self._save()

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._index:
                del self._index[name]
                self._save()
                return True
        return False

    def get(self, name: str) -> Optional[ModelMetadata]:
        return self._index.get(name)

    def get_all(self) -> List[ModelMetadata]:
        return list(self._index.values())

    def get_by_type(self, model_type: ModelType) -> List[ModelMetadata]:
        return [m for m in self._index.values() if m.model_type == model_type]

    def count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in self._index.values():
            key = m.model_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def refresh_timestamps(self, name: str, current_time: str):
        """更新最后使用时间"""
        meta = self._index.get(name)
        if meta:
            meta.last_used = current_time
            self._save()


# ================================================================
# 模型校验
# ================================================================

class ModelVerifier:
    """
    模型校验器 — 计算和验证文件完整性
    """

    @staticmethod
    def calculate_sha256(filepath: Path, chunk_size: int = 8 * 1024 * 1024) -> Optional[str]:
        """计算文件的SHA256哈希值"""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            logger.error(f"SHA256计算失败 {filepath}: {e}")
            return None

    @staticmethod
    def verify(filepath: Path, expected_hash: str) -> bool:
        """验证文件哈希"""
        actual = ModelVerifier.calculate_sha256(filepath)
        return actual == expected_hash if actual else False


# ================================================================
# 主模型管理器
# ================================================================

class ModelManager:
    """
    模型管理器 — 统一管理所有模型

    功能：
    - 扫描磁盘上的模型文件
    - 维护模型索引（JSON）
    - 查询模型信息
    - 文件统计和存储占用
    - 校验完整性
    - 下载框架预留接口

    不执行：
    - 不自动下载模型
    - 不安装任何模型
    - 不修改外部模型文件
    """

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = str(_project_root)
        self._project_root = Path(project_root)
        self._config = ConfigManager()

        # 模型根目录（从配置文件读取）
        model_root_str = self._config.get("paths.models_dir", "data/models")
        self._model_root = self._project_root / model_root_str

        # 索引文件
        self._index_file = self._project_root / "data" / "models" / "index.json"
        self._index = ModelIndex(self._index_file)

        # 扫描器
        self._scanner = ModelScanner(self._model_root)

        # 下载回调
        self._download_callbacks: List[Callable] = []

    # ---- 公开 API ----

    @property
    def model_root(self) -> Path:
        return self._model_root

    @property
    def index(self) -> ModelIndex:
        return self._index

    def get_all_models(self) -> List[ModelMetadata]:
        """获取所有已索引的模型"""
        return self._index.get_all()

    def get_model(self, name: str) -> Optional[ModelMetadata]:
        """按名称获取模型"""
        return self._index.get(name)

    def get_models_by_type(self, model_type: ModelType) -> List[ModelMetadata]:
        """按类型获取模型列表"""
        return self._index.get_by_type(model_type)

    def get_model_counts(self) -> Dict[str, int]:
        """获取各类型模型数量"""
        return self._index.count_by_type()

    def scan_and_index(self, force: bool = False) -> int:
        """
        扫描模型目录并建立索引

        扫描磁盘上所有模型文件，生成索引条目。
        如果已有同名模型且force=False，跳过。

        Args:
            force: 强制重新索引所有文件

        Returns:
            新索引的模型数量
        """
        logger.info(f"开始扫描模型目录: {self._model_root}")
        new_count = 0

        # 扫描每种类型
        for mt in ModelType:
            files = self._scanner.scan_by_type(mt)
            for filepath in files:
                name = filepath.stem
                existing = self._index.get(name)

                if force or existing is None:
                    # 计算基本信息
                    stat = filepath.stat()
                    meta = ModelMetadata(
                        name=name,
                        model_type=mt,
                        filename=filepath.name,
                        file_path=str(filepath),
                        file_size_bytes=stat.st_size,
                        status=ModelStatus.AVAILABLE,
                        installed_at=datetime.now().isoformat(),
                    )
                    self._index.add_or_update(meta)
                    new_count += 1
                    logger.debug(f"索引模型: {name} ({mt.value})")
                elif force:
                    # 更新已有信息
                    stat = filepath.stat()
                    existing.file_size_bytes = stat.st_size
                    self._index.add_or_update(existing)
                    new_count += 1

        logger.info(f"扫描完成: {new_count} 个新索引")
        return new_count

    def register_model_file(self, filepath: Path, model_type: ModelType) -> Optional[ModelMetadata]:
        """
        注册单个模型文件到索引

        Args:
            filepath: 模型文件完整路径
            model_type: 模型类型

        Returns:
            创建的元数据对象，或 None
        """
        if not filepath.exists():
            return None

        name = filepath.stem
        meta = ModelMetadata(
            name=name,
            model_type=model_type,
            filename=filepath.name,
            file_path=str(filepath),
            file_size_bytes=filepath.stat().st_size,
            status=ModelStatus.AVAILABLE,
            installed_at=datetime.now().isoformat(),
        )

        # 尝试计算SHA256
        sha256 = ModelVerifier.calculate_sha256(filepath)
        if sha256:
            meta.sha256_hash = sha256
            meta.status = ModelStatus.VERIFIED

        self._index.add_or_update(meta)
        return meta

    def verify_model(self, name: str) -> bool:
        """
        验证模型文件完整性

        Returns:
            True 如果校验通过
        """
        meta = self._index.get(name)
        if not meta or not meta.sha256_hash:
            return False

        filepath = Path(meta.file_path)
        if not filepath.exists():
            meta.status = ModelStatus.MISSING
            self._index.add_or_update(meta)
            return False

        return ModelVerifier.verify(filepath, meta.sha256_hash)

    def remove_model_index(self, name: str) -> bool:
        """从索引中移除模型（不删除实际文件）"""
        return self._index.remove(name)

    def update_model_last_used(self, name: str):
        """更新模型最后使用时间"""
        ts = datetime.now().isoformat()
        self._index.refresh_timestamps(name, ts)

    def get_storage_stats(self) -> Dict[str, Any]:
        """获取模型存储统计"""
        usage = self._scanner.get_directory_usage()
        usage["indexed_count"] = len(self._index.get_all())
        usage["type_counts"] = self._index.count_by_type()
        return usage

    def get_model_info_summary(self) -> List[Dict[str, Any]]:
        """获取模型信息摘要（供UI表格显示）"""
        results = []
        for meta in self._index.get_all():
            filepath = Path(meta.file_path)
            exists = filepath.exists()
            try:
                size_human = self._human_size(filepath.stat().st_size) if exists else "?"
            except:
                size_human = "?"
            results.append({
                "name": meta.name,
                "type": meta.model_type.display_name,
                "filename": meta.filename,
                "size": size_human,
                "status": meta.status.value,
                "path": meta.file_path if exists else "(缺失)",
            })
        return sorted(results, key=lambda x: x["name"])

    # ---- 下载框架接口 ----

    def on_download_progress(self, callback: Callable):
        """注册下载进度回调"""
        self._download_callbacks.append(callback)

    def start_download(self, url: str, dest_dir: Optional[str] = None) -> Optional[str]:
        """
        启动下载任务（预留接口）

        实际下载逻辑委托给 DownloadManager。
        本方法仅为高层API，不直接执行下载。

        Args:
            url: 下载源URL
            dest_dir: 目标目录

        Returns:
            task_id 或 None（失败时）
        """
        # TODO: 集成 src/download_manager.DownloadManager
        # 当前阶段：仅提供接口，不实现实际下载
        logger.info(f"下载请求: {url}")
        logger.info("注意：实际下载功能将在后续阶段实现")
        return None

    def cancel_download(self, task_id: str) -> bool:
        """取消下载任务（预留接口）"""
        logger.info(f"取消下载: {task_id}")
        return False

    # ---- 内部方法 ----

    @staticmethod
    def _human_size(nbytes: int) -> str:
        """格式化为人类可读的大小字符串"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if nbytes < 1024:
                return f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} TB"


# ================================================================
# 全局单例
# ================================================================

_instance = None


def get_model_manager(project_root: Optional[str] = None) -> ModelManager:
    """获取全局模型管理器实例（单例）"""
    global _instance
    if _instance is None or project_root:
        _instance = ModelManager(project_root)
    return _instance


if __name__ == "__main__":
    # 命令行测试
    mm = ModelManager()
    print(f"模型根目录: {mm.model_root}")
    print(f"已索引模型数: {len(mm.get_all_models())}")
    stats = mm.get_storage_stats()
    print(f"存储使用: {stats['total_mb']}MB ({stats['file_count']}个文件)")
    print(f"类型分布: {stats.get('type_counts', {})}")
    print("\n扫描并建立索引...")
    new_count = mm.scan_and_index(force=True)
    print(f"新索引: {new_count} 个模型")
    stats2 = mm.get_storage_stats()
    print(f"现在存储使用: {stats2['total_mb']}MB ({stats2['file_count']}个文件)")
