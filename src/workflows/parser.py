"""工作流 JSON 解析器

解析 ComfyUI 工作流 JSON 格式，提供：
- 从 JSON 字符串/文件加载工作流
- 将工作流转换为 Python 对象
- 将 Python 对象导出为 JSON
- 节点连接校验
- 参数绑定验证
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from src.logger import get_logger
from src.workflows.nodes import NodeSignature, NodeRegistry

logger = get_logger("workflow.parser")


@dataclass
class Connection:
    """节点之间的连接"""
    from_node: str             # 源节点 ID
    from_port: int             # 源端口索引
    to_node: str               # 目标节点 ID
    to_port: str               # 目标端口名
    data_type: str = ""        # 数据类型

    def to_dict(self) -> dict:
        return {
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node": self.to_node,
            "to_port": self.to_port,
            "data_type": self.data_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Connection":
        return cls(
            from_node=data["from_node"],
            from_port=data["from_port"],
            to_node=data["to_node"],
            to_port=data["to_port"],
            data_type=data.get("data_type", ""),
        )


@dataclass
class NodeInstance:
    """工作流中的节点实例"""
    node_id: str               # 节点 ID (字符串)
    node_class: str            # 节点类名
    params: Dict[str, Any] = field(default_factory=dict)  # 参数值
    position: Tuple[int, int] = (0, 0)  # 画布位置
    size: Tuple[int, int] = (200, 100)   # 节点尺寸
    properties: Dict[str, Any] = field(default_factory=dict)  # 额外属性

    def get_param(self, name: str, default: Any = None) -> Any:
        """获取参数值"""
        return self.params.get(name, default)

    def to_dict(self) -> dict:
        result = {
            "node_class": self.node_class,
            "params": self.params,
            "position": list(self.position),
            "size": list(self.size),
            "properties": self.properties,
        }
        return result

    @classmethod
    def from_dict(cls, node_id: str, data: dict) -> "NodeInstance":
        return cls(
            node_id=node_id,
            node_class=data["node_class"],
            params=data.get("params", {}),
            position=tuple(data.get("position", [0, 0])),
            size=tuple(data.get("size", [200, 100])),
            properties=data.get("properties", {}),
        )


@dataclass
class Workflow:
    """工作流对象 — 解析后的完整工作流"""
    name: str = ""
    nodes: Dict[str, NodeInstance] = field(default_factory=dict)
    connections: List[Connection] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)  # 元数据

    @property
    def node_ids(self) -> List[str]:
        """所有节点 ID"""
        return list(self.nodes.keys())

    @property
    def node_classes(self) -> List[str]:
        """所有节点类名"""
        return [n.node_class for n in self.nodes.values()]

    def get_node(self, node_id: str) -> Optional[NodeInstance]:
        """获取节点实例"""
        return self.nodes.get(node_id)

    def get_node_connections(self, node_id: str) -> List[Connection]:
        """获取节点的所有连接"""
        return [c for c in self.connections
                if c.from_node == node_id or c.to_node == node_id]

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串"""
        return json.dumps({
            "name": self.name,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "connections": [c.to_dict() for c in self.connections],
            "meta": self.meta,
        }, indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Workflow":
        """从 JSON 字符串创建工作流"""
        data = json.loads(json_str)
        return cls._parse(data)

    @classmethod
    def from_file(cls, file_path: str) -> "Workflow":
        """从文件加载工作流"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"工作流文件不存在: {file_path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._parse(data)

    @classmethod
    def _parse(cls, data: dict) -> "Workflow":
        """解析 JSON 数据为 Workflow 对象"""
        workflow = cls()
        workflow.name = data.get("name", "Untitled")
        workflow.meta = data.get("meta", {})

        # 解析节点
        for node_id, node_data in data.get("nodes", {}).items():
            workflow.nodes[node_id] = NodeInstance.from_dict(node_id, node_data)

        # 解析连接
        for conn_data in data.get("connections", []):
            workflow.connections.append(Connection.from_dict(conn_data))

        return workflow

    def validate(self) -> Tuple[bool, List[str]]:
        """
        校验工作流完整性

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 检查是否有节点
        if not self.nodes:
            errors.append("工作流没有节点")
            return False, errors

        # 检查每个节点的参数类型
        for node_id, node in self.nodes.items():
            sig = NodeRegistry.get(node.node_class)
            if sig is None:
                errors.append(f"未知节点类: {node.node_class}")
                continue

            # 检查必填参数
            for param in sig.input_params:
                if not param.optional and param.name not in node.params:
                    errors.append(
                        f"节点 {node_id} 缺少必填参数: {param.name}"
                    )

        # 检查连接类型兼容性
        for conn in self.connections:
            from_node = self.nodes.get(conn.from_node)
            to_node = self.nodes.get(conn.to_node)
            if from_node and to_node:
                from_sig = NodeRegistry.get(from_node.node_class)
                to_sig = NodeRegistry.get(to_node.node_class)
                if from_sig and to_sig:
                    # 检查输出端口是否存在
                    if conn.from_port >= len(from_sig.output_params):
                        errors.append(
                            f"节点 {conn.from_node} 输出端口 {conn.from_port} 不存在"
                        )

        return len(errors) == 0, errors
