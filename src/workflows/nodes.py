"""工作流节点类型系统

定义 ComfyUI 工作流中所有节点的元数据：
- 内置核心节点 (ComfyUI 自带)
- 社区扩展节点 (ComfyUI-Manager 安装)

每个节点定义了：输入/输出签名、参数 schema、默认值。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(Enum):
    """节点来源分类"""
    BUILTIN = "builtin"      # ComfyUI 原生节点
    COMMUNITY = "community"  # 社区扩展节点
    CUSTOM = "custom"        # 用户自定义节点


class ParamType(Enum):
    """节点参数类型"""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "boolean"
    IMAGE = "image"
    MASK = "mask"
    LATENT = "latent"
    CONDITIONING = "conditioning"
    CLIP = "clip"
    VAE = "vae"
    MODEL = "model"
    CHOICE = "choice"      # 下拉选项


@dataclass
class ParamInfo:
    """节点参数信息"""
    name: str                    # 参数名
    param_type: ParamType        # 参数类型
    display_name: str = ""       # 显示名称
    default: Any = None          # 默认值
    min_val: Optional[float] = None  # 最小值
    max_val: Optional[float] = None  # 最大值
    step: float = 1              # 步进
    choices: List[str] = field(default_factory=list)  # 选项列表
    tooltip: str = ""            # 提示文字
    visible: bool = True         # 是否可见
    advanced: bool = False       # 是否高级参数

    def to_dict(self) -> dict:
        d = asdict(self)
        d["param_type"] = self.param_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ParamInfo":
        data = data.copy()
        if "param_type" in data:
            data["param_type"] = ParamType(data["param_type"])
        return cls(**data)


@dataclass
class PortInfo:
    """节点端口信息 (输入/输出)"""
    name: str
    param_type: ParamType
    optional: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["param_type"] = self.param_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PortInfo":
        data = data.copy()
        if "param_type" in data:
            data["param_type"] = ParamType(data["param_type"])
        return cls(**data)


@dataclass
class NodeSignature:
    """节点签名 — 定义一个节点的完整接口"""
    node_class: str                      # 类名，如 "KSampler"
    display_name: str                    # 显示名称
    node_type: NodeType = NodeType.BUILTIN
    category: str = ""                   # 分类
    description: str = ""                # 描述
    input_params: List[ParamInfo] = field(default_factory=list)     # 输入
    output_params: List[ParamInfo] = field(default_factory=list)    # 输出
    extra_info: Dict[str, Any] = field(default_factory=dict)       # 额外信息

    def get_input_schema(self) -> dict:
        """获取输入参数 schema (用于 UI 表单)"""
        return {p.name: p.to_dict() for p in self.input_params}

    def get_output_schema(self) -> dict:
        """获取输出参数 schema"""
        return {p.name: p.to_dict() for p in self.output_params}

    def to_dict(self) -> dict:
        return {
            "node_class": self.node_class,
            "display_name": self.display_name,
            "node_type": self.node_type.value,
            "category": self.category,
            "description": self.description,
            "input_params": [p.to_dict() for p in self.input_params],
            "output_params": [p.to_dict() for p in self.output_params],
            "extra_info": self.extra_info,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NodeSignature":
        data = data.copy()
        if "node_type" in data:
            data["node_type"] = NodeType(data["node_type"])
        if "input_params" in data:
            data["input_params"] = [
                ParamInfo.from_dict(p) for p in data["input_params"]
            ]
        if "output_params" in data:
            data["output_params"] = [
                ParamInfo.from_dict(p) for p in data["output_params"]
            ]
        return cls(**data)


# ============================================================
# 预定义节点注册表
# ============================================================

class NodeRegistry:
    """节点签名注册表"""

    _signatures: Dict[str, NodeSignature] = {}

    @classmethod
    def register(cls, signature: NodeSignature):
        """注册节点签名"""
        cls._signatures[signature.node_class] = signature

    @classmethod
    def get(cls, node_class: str) -> Optional[NodeSignature]:
        """查找节点签名"""
        return cls._signatures.get(node_class)

    @classmethod
    def get_all(cls) -> List[NodeSignature]:
        """获取所有注册的签名"""
        return list(cls._signatures.values())

    @classmethod
    def get_by_category(cls, category: str) -> List[NodeSignature]:
        """按分类获取签名"""
        return [s for s in cls._signatures.values() if s.category == category]

    @classmethod
    def has(cls, node_class: str) -> bool:
        """检查是否已注册"""
        return node_class in cls._signatures
