"""参数绑定引擎

实现工作流参数的可视化绑定：
- 将节点参数绑定到 UI 表单控件
- 支持绑定表达式 (如 "seed -> slider_1.value")
- 支持模板参数化 (subgraph 输入端口映射)

绑定语法:
  - 直接值: seed = 12345
  - 控件绑定: seed = slider_1.value
  - 表达式: steps = steps_slider * 2
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from src.logger import get_logger

logger = get_logger("workflow.bindings")


@dataclass
class Binding:
    """单个参数绑定"""
    target_node: str             # 目标节点 ID
    target_param: str            # 目标参数名
    binding_type: str            # 类型: "value", "control", "expression"
    value: Any = None            # 直接值
    control_id: str = ""         # 绑定的控件 ID
    expression: str = ""         # 表达式
    description: str = ""        # 描述

    def to_dict(self) -> dict:
        d = {
            "target_node": self.target_node,
            "target_param": self.target_param,
            "binding_type": self.binding_type,
        }
        if self.value is not None:
            d["value"] = self.value
        if self.control_id:
            d["control_id"] = self.control_id
        if self.expression:
            d["expression"] = self.expression
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Binding":
        return cls(
            target_node=data["target_node"],
            target_param=data["target_param"],
            binding_type=data["binding_type"],
            value=data.get("value"),
            control_id=data.get("control_id", ""),
            expression=data.get("expression", ""),
            description=data.get("description", ""),
        )


class BindingEngine:
    """
    参数绑定引擎

    管理工作流中所有参数绑定关系。
    支持动态更新绑定值。
    """

    def __init__(self):
        self._bindings: Dict[str, Dict[str, Binding]] = {}  # {node_id: {param: Binding}}
        self._controls: Dict[str, Any] = {}  # {control_id: value}
        self._listeners: List[Callable] = []

    def add_binding(self, binding: Binding):
        """添加参数绑定"""
        node_id = binding.target_node
        if node_id not in self._bindings:
            self._bindings[node_id] = {}
        self._bindings[node_id][binding.target_param] = binding
        logger.info(f"添加绑定: {node_id}.{binding.target_param} = {binding.binding_type}")
        self._notify_listeners(binding)

    def add_control(self, control_id: str, value: Any):
        """添加控件 (绑定目标)"""
        self._controls[control_id] = value
        logger.info(f"添加控件: {control_id} = {value}")

    def update_control(self, control_id: str, value: Any):
        """更新控件值"""
        if control_id in self._controls:
            self._controls[control_id] = value
            self._notify_listeners(None)

    def get_binding(self, node_id: str, param: str) -> Optional[Binding]:
        """获取绑定"""
        return self._bindings.get(node_id, {}).get(param)

    def get_all_bindings(self) -> Dict[str, Dict[str, Binding]]:
        """获取所有绑定"""
        return self._bindings

    def get_control_value(self, control_id: str) -> Optional[Any]:
        """获取控件值"""
        return self._controls.get(control_id)

    def resolve_value(self, node_id: str, param: str) -> Any:
        """
        解析绑定值

        根据绑定类型返回实际值:
        - "value": 直接返回
        - "control": 从控件获取
        - "expression": 计算表达式
        """
        binding = self.get_binding(node_id, param)
        if binding is None:
            return None

        if binding.binding_type == "value":
            return binding.value
        elif binding.binding_type == "control":
            return self.get_control_value(binding.control_id)
        elif binding.binding_type == "expression":
            return self._eval_expression(binding.expression)
        return None

    def _eval_expression(self, expr: str) -> Any:
        """评估表达式 (安全求值)"""
        # TODO: 实现安全的表达式求值器
        return None

    def on_change(self, callback: Callable):
        """注册变更监听器"""
        self._listeners.append(callback)

    def _notify_listeners(self, binding: Optional[Binding]):
        """通知所有监听器"""
        for cb in self._listeners:
            try:
                cb(binding)
            except Exception as e:
                logger.error(f"绑定变更通知失败: {e}")

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "bindings": {
                nid: {param: b.to_dict() for param, b in params.items()}
                for nid, params in self._bindings.items()
            },
            "controls": self._controls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BindingEngine":
        """反序列化"""
        engine = cls()
        for node_id, params in data.get("bindings", {}).items():
            for param, binding_data in params.items():
                engine.add_binding(Binding.from_dict(binding_data))
        engine._controls = data.get("controls", {})
        return engine
