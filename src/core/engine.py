"""
Engine Adapter 接口层

定义统一的 AI 推理引擎抽象。

所有底层引擎（ComfyUI/Diffusers/ONNX/OpenVINO/CUDA/Metal）
必须实现 EngineAdapter 接口。

业务层只调用此接口，不直接依赖任何具体引擎。

未来扩展：
- src/engines/comfyui/ — ComfyUI 适配器
- src/engines/diffusers/ — Diffusers 适配器
- src/engines/onnx/    — ONNX Runtime 适配器
- src/engines/openvino/ — OpenVINO 适配器
- src/engines/cuda/    — CUDA 原生接口
- src/engines/metal/   — Apple Metal 适配器
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple


class EngineCapability(Enum):
    """引擎能力类型"""
    IMAGE_GENERATION = "image_generation"       # 图像生成
    IMAGE_UPSCALE = "image_upscale"             # 图像放大
    IMAGE_EDIT = "image_edit"                   # 图像编辑
    BACKGROUND_REMOVE = "background_remove"     # 背景移除
    FACE_ENHANCE = "face_enhance"               # 人脸增强
    TEXT_TO_IMAGE = "text_to_image"             # 文本→图像
    IMAGE_TO_IMAGE = "image_to_image"           # 图像→图像
    INPAINTING = "inpainting"                   # 局部重绘
    OUTPAINTING = "outpainting"                 # 扩展绘画


@dataclass
class EngineInfo:
    """引擎信息"""
    name: str
    version: str
    capabilities: List[EngineCapability] = field(default_factory=list)
    supported_backends: List[str] = field(default_factory=list)
    memory_requirements_mb: int = 0
    description: str = ""

    def supports(self, capability: EngineCapability) -> bool:
        return capability in self.capabilities


@dataclass
class InferenceRequest:
    """推理请求"""
    capability: EngineCapability
    engine_type: str                      # 引擎类型标识
    model_path: str = ""                  # 模型路径
    input_data: Any = None                # 输入数据
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None   # 进度回调


@dataclass
class InferenceResult:
    """推理结果"""
    success: bool
    output: Any = None                    # 输出结果
    elapsed_seconds: float = 0.0          # 耗时
    engine_used: str = ""                 # 使用的引擎
    status_message: str = ""              # 状态消息
    warnings: List[str] = field(default_factory=list)


class EngineAdapter(ABC):
    """
    AI 推理引擎适配器（抽象基类）

    所有底层推理引擎必须实现此接口。
    业务层通过此接口调用 AI 能力，不直接依赖具体引擎。

    实现要求：
    - 实现 get_info() 返回引擎元数据
    - 实现 execute() 执行推理任务
    - 线程安全
    - 资源自动释放
    """

    @abstractmethod
    def get_info(self) -> EngineInfo:
        """获取引擎信息"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """引擎是否可用"""
        ...

    @abstractmethod
    def execute(self, request: InferenceRequest) -> InferenceResult:
        """
        执行推理任务

        Args:
            request: 推理请求

        Returns:
            推理结果
        """
        ...

    @abstractmethod
    def prepare_model(self, model_path: str) -> bool:
        """
        准备模型（加载/缓存/优化）

        Args:
            model_path: 模型文件路径

        Returns:
            是否成功
        """
        ...

    @abstractmethod
    def release_resources(self):
        """释放所有资源"""
        ...

    @abstractmethod
    def get_memory_usage(self) -> Dict[str, int]:
        """
        获取当前内存使用情况

        Returns:
            {"total_mb": int, "gpu_mb": int, "cpu_mb": int}
        """
        ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release_resources()


# ================================================================
# Engine Registry（引擎注册表）
# ================================================================

class EngineRegistry:
    """
    引擎注册表

    管理所有可用的推理引擎适配器。
    运行时根据需求选择最合适的引擎。

    使用方式：
        reg = EngineRegistry()
        reg.register(ComfyUIEngine())
        adapter = reg.get_best("image_upscale")
        result = adapter.execute(InferenceRequest(...))
    """

    _instance = None
    _engines: Dict[str, EngineAdapter] = {}

    @classmethod
    def instance(cls) -> "EngineRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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
        """按名称获取引擎适配器"""
        return self._engines.get(engine_name)

    def get_best_for_capability(self, capability: EngineCapability) -> Optional[EngineAdapter]:
        """
        获取最适合某个能力的引擎

        优先级：
        1. Intel XPU (默认首选)
        2. NVIDIA CUDA
        3. DirectML
        4. 其他
        """
        candidates = []
        for name, adapter in self._engines.items():
            if not adapter.is_available():
                continue
            if adapter.get_info().supports(capability):
                candidates.append(adapter)

        if not candidates:
            return None

        # 按优先级排序
        priority = {
            "intel_xpu": 0,
            "nvidia_cuda": 1,
            "directml": 2,
            "apple_mps": 3,
            "amd_rocm": 4,
        }
        candidates.sort(key=lambda a: priority.get(a.get_info().name, 99))
        return candidates[0]

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有注册的引擎及其状态"""
        result = []
        for name, adapter in self._engines.items():
            info = adapter.get_info()
            try:
                mem = adapter.get_memory_usage()
            except Exception:
                mem = {}
            result.append({
                "name": info.name,
                "version": info.version,
                "available": adapter.is_available(),
                "capabilities": [c.value for c in info.capabilities],
                "memory": mem,
            })
        return result
