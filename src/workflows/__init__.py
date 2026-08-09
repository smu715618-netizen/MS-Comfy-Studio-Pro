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

# WorkflowManager lives in src/workflows.py (a module, not the package).
# Use importlib to load it without circular import.
import importlib.util as _ilu, sys as _sys, pathlib as _pl
_wf_py = _pl.Path(__file__).parent.parent / "workflows.py"
if _wf_py.exists():
    _wf_spec = _ilu.spec_from_file_location("src_workflows_module", _wf_py)
    _wf_mod = _ilu.module_from_spec(_wf_spec)
    _wf_spec.loader.exec_module(_wf_mod)
    WorkflowManager = _wf_mod.WorkflowManager
else:
    WorkflowManager = None

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
    "WorkflowManager",
]
