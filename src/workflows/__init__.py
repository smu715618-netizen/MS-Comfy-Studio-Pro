# 工作流系统包

"""
工作流系统模块

管理 ComfyUI 工作流的生命周期：
- 节点签名定义 (nodes.py, signatures.py)
- 工作流 JSON 解析/生成 (parser.py)
- 参数绑定引擎 (bindings.py)
- 工作流管理 (workflows.py)

工作流格式: ComfyUI JSON 格式
存储位置: data/workflows/{category}/{name}.json
"""

from src.workflows.nodes import NodeSignature, NodeType, ParamType, NodeRegistry
from src.workflows.parser import Workflow, NodeInstance, Connection
from src.workflows.bindings import Binding, BindingEngine

__all__ = [
    "NodeSignature",
    "NodeType",
    "ParamType",
    "NodeRegistry",
    "Workflow",
    "NodeInstance",
    "Connection",
    "Binding",
    "BindingEngine",
]
