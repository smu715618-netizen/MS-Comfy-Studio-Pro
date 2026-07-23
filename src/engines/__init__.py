# Engine Adapters (AI 推理引擎适配层)

"""
统一的 AI 引擎抽象接口和注册管理。

所有底层推理引擎（ComfyUI/Diffusers/ONNX/OpenVINO/CUDA/Metal）
必须实现 EngineAdapter 接口。

业务层通过 EngineManager 调用引擎，不直接依赖任何具体引擎。

目录结构：
  src/engines/__init__.py       — 统一入口 + EngineManager
  src/engines/base.py           — EngineAdapter ABC 基类
  src/engines/comfyui/          — ComfyUI 适配器
  src/engines/diffusers/        — Diffusers 适配器（预留）
  src/engines/onnx/             — ONNX Runtime 适配器（预留）
  src/engines/openvino/         — OpenVINO 适配器（预留）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set


class EngineCapability(Enum):
    """引擎支持的能力类型"""
    IMAGE_GENERATION = "image_generation"
    IMAGE_UPSCALE = "image_upscale"
    IMAGE_EDIT = "image_edit"
    BACKGROUND_REMOVE = "background_remove"
    FACE_ENHANCE = "face_enhance"
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    INPAINTING = "inpainting"
    OUTPAINTING = "outpainting"
    PORTRAIT_RETOUCH = "portrait_retouch"
    PRODUCT_PHOTO = "product_photo"


class EngineBackend(Enum):
    """推理后端框架"""
    XPU = "xpu"
    DIRECTML = "directml"
    CUDA = "cuda"
    ROCM = "rocm"
    MPS = "mps"
    CPU = "cpu"
    ONNX = "onnx"
    OPENVINO = "openvino"


@dataclass
class EngineInfo:
    """引擎信息"""
    name: str
    version: str
    description: str = ""
    capabilities: List[EngineCapability] = field(default_factory=list)
    supported_backends: List[EngineBackend] = field(default_factory=list)
    memory_requirements_mb: int = 0
    author: str = ""
    homepage: str = ""

    def supports(self, capability: EngineCapability) -> bool:
        return capability in self.capabilities

    def supports_backend(self, backend: EngineBackend) -> bool:
        return backend in self.supported_backends

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        d['capabilities'] = [c.value for c in self.capabilities]
        d['supported_backends'] = [b.value for b in self.supported_backends]
        return d


@dataclass
class InferenceTask:
    """推理任务"""
    task_id: str
    capability: EngineCapability
    engine_name: str = ""                # 目标引擎名称
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_data: Any = None               # 输入数据（路径或字节）
    output_path: str = ""                # 输出文件路径
    progress_callback: Optional[Callable] = None
    status: str = "pending"              # pending/scheduling/executing/completed/failed/cancelled
    error_message: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class InferenceResult:
    """推理结果"""
    success: bool
    task_id: str = ""
    output_path: str = ""               # 输出文件路径
    elapsed_seconds: float = 0.0        # 耗时
    engine_used: str = ""               # 使用的引擎
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "output_path": self.output_path,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "engine_used": self.engine_used,
            "warnings": self.warnings,
        }


class EngineAdapter(ABC):
    """
    AI 推理引擎适配器 — 抽象基类

    所有底层引擎必须实现此接口的全部方法。
    业务层不直接调用引擎，只通过 EngineManager 提交任务。

    必须实现的抽象方法：
    - get_info() — 返回引擎元信息
    - is_available() — 检查引擎是否可用
    - execute() — 执行推理任务
    - prepare_model() — 准备模型文件
    - release_resources() — 释放资源
    - get_memory_usage() — 获取内存使用统计
    """

    @abstractmethod
    def get_info(self) -> EngineInfo:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def execute(self, task: InferenceTask) -> InferenceResult:
        ...

    @abstractmethod
    def prepare_model(self, model_path: str) -> bool:
        ...

    @abstractmethod
    def release_resources(self):
        ...

    @abstractmethod
    def get_memory_usage(self) -> Dict[str, int]:
        ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release_resources()


class EngineManager:
    """
    引擎管理器 — 单例模式

    统一管理所有已注册的引擎适配器。
    提供引擎选择、能力查询、状态监控等高级功能。
    """

    _instance = None

    @classmethod
    def instance(cls) -> 'EngineManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._engines: Dict[str, EngineAdapter] = {}
        self._default_engine: Optional[str] = None

    def register(self, adapter: EngineAdapter):
        """注册引擎适配器"""
        info = adapter.get_info()
        self._engines[info.name] = adapter

    def unregister(self, engine_name: str) -> bool:
        """注销引擎适配器"""
        if engine_name in self._engines:
            del self._engines[engine_name]
            return True
        return False

    def get(self, engine_name: str) -> Optional[EngineAdapter]:
        """按名称获取引擎"""
        return self._engines.get(engine_name)

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有已注册引擎及其状态"""
        result = []
        for name, engine in self._engines.items():
            try:
                mem = engine.get_memory_usage()
            except Exception:
                mem = {}
            result.append({
                "name": name,
                "available": engine.is_available(),
                "memory": mem,
            })
        return result

    def get_best_for_capability(self, capability: EngineCapability) -> Optional[EngineAdapter]:
        """
        根据能力需求选择最佳引擎

        优先级：
        1. XPU (Intel Arc 默认)
        2. CUDA (NVIDIA)
        3. 其他
        """
        candidates = []
        priority_order = {EngineBackend.XPU: 0, EngineBackend.CUDA: 1, EngineBackend.DIRECTML: 2}

        for engine in self._engines.values():
            if engine.is_available() and engine.get_info().supports(capability):
                for backend in engine.get_info().supported_backends:
                    if backend in priority_order:
                        candidates.append((priority_order[backend], engine))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        return None

    def select_engine_for_task(self, task: InferenceTask) -> Optional[EngineAdapter]:
        """为任务自动选择最佳引擎"""
        if task.engine_name:
            return self._engines.get(task.engine_name)
        return self.get_best_for_capability(task.capability)

    @property
    def available_engines(self) -> List[str]:
        """可用的引擎名称列表"""
        return [n for n, e in self._engines.items() if e.is_available()]


if __name__ == "__main__":
    manager = EngineManager.instance()
    print(f"Registered engines: {[e for e in manager.list_all()]}")
