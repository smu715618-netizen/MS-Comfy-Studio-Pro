"""工作流节点签名测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.workflows.nodes import NodeSignature, NodeType, ParamType, NodeRegistry


class TestParamType:
    """测试参数类型"""

    def test_all_types_exist(self):
        """测试所有参数类型枚举值存在"""
        assert ParamType.STRING.value == "string"
        assert ParamType.INT.value == "int"
        assert ParamType.FLOAT.value == "float"
        assert ParamType.BOOL.value == "boolean"
        assert ParamType.IMAGE.value == "image"
        assert ParamType.LATENT.value == "latent"
        assert ParamType.MODEL.value == "model"
        assert ParamType.CHOICE.value == "choice"


class TestNodeSignature:
    """测试节点签名"""

    def test_create_signature(self):
        """测试创建节点签名"""
        sig = NodeSignature(
            node_class="TestNode",
            display_name="测试节点",
            node_type=NodeType.BUILTIN,
            category="test",
            input_params=[
                ParamInfo(name="input1", param_type=ParamType.STRING),
            ],
            output_params=[
                ParamInfo(name="output1", param_type=ParamType.IMAGE),
            ],
        )
        assert sig.node_class == "TestNode"
        assert sig.display_name == "测试节点"
        assert len(sig.input_params) == 1
        assert len(sig.output_params) == 1

    def test_to_dict_roundtrip(self):
        """测试序列化/反序列化"""
        sig = NodeSignature(
            node_class="RoundTrip",
            display_name="往返测试",
            node_type=NodeType.BUILTIN,
            input_params=[
                ParamInfo(name="x", param_type=ParamType.INT, default=42),
            ],
            output_params=[
                ParamInfo(name="y", param_type=ParamType.INT),
            ],
        )
        data = sig.to_dict()
        restored = NodeSignature.from_dict(data)
        assert restored.node_class == sig.node_class
        assert restored.display_name == sig.display_name
        assert len(restored.input_params) == 1
        assert restored.input_params[0].name == "x"


class TestNodeRegistry:
    """测试节点注册表"""

    def test_register_and_get(self):
        """测试注册和查找"""
        sig = NodeSignature(
            node_class="TestRegister",
            display_name="测试注册",
            node_type=NodeType.BUILTIN,
        )
        NodeRegistry.register(sig)
        assert NodeRegistry.has("TestRegister")
        assert NodeRegistry.get("TestRegister") is sig

    def test_get_all(self):
        """测试获取所有签名"""
        all_sigs = NodeRegistry.get_all()
        assert len(all_sigs) > 0  # 应该至少有预定义的签名

    def test_predefined_signatures_loaded(self):
        """测试预定义签名已加载"""
        from src.workflows import signatures
        assert NodeRegistry.has("CheckpointLoaderSimple")
        assert NodeRegistry.has("KSampler")
        assert NodeRegistry.has("CLIPTextEncode")
