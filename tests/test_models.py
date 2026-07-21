"""
模型管理测试
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import ModelManager, ModelType, ModelStatus, ModelMetadata


class TestModelMetadata:
    """测试模型元数据"""

    def test_serialization(self):
        """测试序列化/反序列化"""
        meta = ModelMetadata(
            name="test-model",
            model_type=ModelType.CHECKPOINT,
            filename="test.safetensors",
            file_size_bytes=1234567,
        )
        data = meta.to_dict()
        restored = ModelMetadata.from_dict(data)

        assert restored.name == meta.name
        assert restored.model_type == meta.model_type
        assert restored.filename == meta.filename
        assert restored.file_size_bytes == meta.file_size_bytes

    def test_status_enum(self):
        """测试状态枚举"""
        meta = ModelMetadata(
            name="test",
            model_type=ModelType.VAE,
            filename="test.pt",
        )
        assert meta.status == ModelStatus.AVAILABLE
        meta.status = ModelStatus.VERIFYING
        assert meta.status == ModelStatus.VERIFYING


class TestModelManager:
    """测试模型管理器"""

    def setup_method(self):
        """每次测试前创建临时目录"""
        self.tmpdir = tempfile.mkdtemp()
        self.manager = ModelManager(data_dir=self.tmpdir)

    def test_add_and_get_model(self):
        """测试添加和获取模型"""
        meta = ModelMetadata(
            name="test-model",
            model_type=ModelType.CHECKPOINT,
            filename="test.safetensors",
        )
        self.manager.add_model(meta)
        retrieved = self.manager.get_model("test-model")
        assert retrieved is not None
        assert retrieved.name == "test-model"

    def test_remove_model(self):
        """测试移除模型"""
        meta = ModelMetadata(
            name="test-remove",
            model_type=ModelType.VAE,
            filename="test.vae.pt",
        )
        self.manager.add_model(meta)
        assert self.manager.remove_model("test-remove") is True
        assert self.manager.get_model("test-remove") is None

    def test_get_models_by_type(self):
        """测试按类型获取模型"""
        for i in range(3):
            self.manager.add_model(ModelMetadata(
                name=f"ckpt-{i}",
                model_type=ModelType.CHECKPOINT,
                filename=f"ckpt-{i}.safetensors",
            ))

        self.manager.add_model(ModelMetadata(
            name="vae-1",
            model_type=ModelType.VAE,
            filename="vae-1.pt",
        ))

        ckpts = self.manager.get_models_by_type(ModelType.CHECKPOINT)
        assert len(ckpts) == 3

        vaes = self.manager.get_models_by_type(ModelType.VAE)
        assert len(vaes) == 1

    def test_storage_usage(self):
        """测试存储统计"""
        usage = self.manager.get_storage_usage()
        assert "total_bytes" in usage
        assert "total_mb" in usage
        assert "by_type" in usage
        assert "model_count" in usage
        assert usage["model_count"] == 0

    def test_index_persistence(self):
        """测试索引持久化"""
        meta = ModelMetadata(
            name="persistent-model",
            model_type=ModelType.LORA,
            filename="lora.safetensors",
        )
        self.manager.add_model(meta)

        # 重新加载管理器
        manager2 = ModelManager(data_dir=self.tmpdir)
        retrieved = manager2.get_model("persistent-model")
        assert retrieved is not None
        assert retrieved.name == "persistent-model"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
