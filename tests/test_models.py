"""
模型管理测试

测试 ModelManager 的完整 API：
- 初始化（project_root）
- 模型注册（register_model_file）
- 模型查询（get_model / get_all_models / get_models_by_type）
- 索引删除（remove_model_index）
- 存储统计（get_storage_stats）
- 索引持久化（同目录重建实例）
- 扫描索引（scan_and_index）
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    ModelManager, ModelType, ModelStatus, ModelMetadata, ModelScanner,
    ModelIndex, ModelVerifier,
)


class TestModelMetadata:
    """测试模型元数据序列化"""

    def test_serialization_roundtrip(self):
        """测试 to_dict / from_dict 往返"""
        meta = ModelMetadata(
            name="test-model",
            model_type=ModelType.CHECKPOINT,
            filename="test.safetensors",
            file_size_bytes=1234567,
            sha256_hash="abc123",
            status=ModelStatus.VERIFIED,
            tags=["test", "portrait"],
        )
        data = meta.to_dict()
        restored = ModelMetadata.from_dict(data)

        assert restored.name == "test-model"
        assert restored.model_type == ModelType.CHECKPOINT
        assert restored.filename == "test.safetensors"
        assert restored.file_size_bytes == 1234567
        assert restored.sha256_hash == "abc123"
        assert restored.status == ModelStatus.VERIFIED
        assert restored.tags == ["test", "portrait"]

    def test_status_enum_values(self):
        """测试状态枚举值"""
        assert ModelStatus.AVAILABLE.value == "available"
        assert ModelStatus.DOWNLOADING.value == "downloading"
        assert ModelStatus.VERIFYING.value == "verifying"
        assert ModelStatus.VERIFIED.value == "verified"
        assert ModelStatus.CORRUPTED.value == "corrupted"
        assert ModelStatus.MISSING.value == "missing"

    def test_model_type_display_name(self):
        """测试模型类型显示名称"""
        assert ModelType.CHECKPOINT.display_name == "Checkpoint"
        assert ModelType.LORA.display_name == "LoRA"
        assert ModelType.VAE.display_name == "VAE"

    def test_model_type_supported_formats(self):
        """测试模型类型支持格式"""
        assert ".safetensors" in ModelType.CHECKPOINT.supported_formats
        assert ".ckpt" in ModelType.CHECKPOINT.supported_formats
        assert ".safetensors" in ModelType.LORA.supported_formats


class TestModelIndex:
    """测试索引持久化"""

    def test_add_and_get(self):
        """测试添加和获取模型"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx = ModelIndex(index_file)
            meta = ModelMetadata(
                name="test-model",
                model_type=ModelType.CHECKPOINT,
                filename="test.safetensors",
            )
            idx.add_or_update(meta)
            retrieved = idx.get("test-model")
            assert retrieved is not None
            assert retrieved.name == "test-model"

    def test_persistence(self):
        """测试索引持久化到磁盘"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx1 = ModelIndex(index_file)
            meta = ModelMetadata(
                name="persistent-model",
                model_type=ModelType.LORA,
                filename="lora.safetensors",
            )
            idx1.add_or_update(meta)
            del idx1

            # 重新加载
            idx2 = ModelIndex(index_file)
            retrieved = idx2.get("persistent-model")
            assert retrieved is not None
            assert retrieved.name == "persistent-model"
            assert retrieved.model_type == ModelType.LORA

    def test_get_by_type(self):
        """测试按类型查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx = ModelIndex(index_file)
            for i in range(3):
                idx.add_or_update(ModelMetadata(
                    name=f"ckpt-{i}",
                    model_type=ModelType.CHECKPOINT,
                    filename=f"ckpt-{i}.safetensors",
                ))
            idx.add_or_update(ModelMetadata(
                name="vae-1",
                model_type=ModelType.VAE,
                filename="vae-1.pt",
            ))

            ckpts = idx.get_by_type(ModelType.CHECKPOINT)
            assert len(ckpts) == 3
            vaes = idx.get_by_type(ModelType.VAE)
            assert len(vaes) == 1

    def test_remove(self):
        """测试删除索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx = ModelIndex(index_file)
            meta = ModelMetadata(
                name="to-remove",
                model_type=ModelType.VAE,
                filename="remove.pt",
            )
            idx.add_or_update(meta)
            assert idx.get("to-remove") is not None
            assert idx.remove("to-remove") is True
            assert idx.get("to-remove") is None
            # 重复删除返回 False
            assert idx.remove("to-remove") is False

    def test_count_by_type(self):
        """测试按类型计数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx = ModelIndex(index_file)
            for i in range(2):
                idx.add_or_update(ModelMetadata(
                    name=f"ckpt-{i}",
                    model_type=ModelType.CHECKPOINT,
                    filename=f"ckpt-{i}.safetensors",
                ))
            counts = idx.count_by_type()
            assert counts.get("checkpoints", 0) == 2

    def test_get_all(self):
        """测试获取全部模型"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            idx = ModelIndex(index_file)
            idx.add_or_update(ModelMetadata(
                name="a", model_type=ModelType.CHECKPOINT, filename="a.safetensors",
            ))
            idx.add_or_update(ModelMetadata(
                name="b", model_type=ModelType.LORA, filename="b.safetensors",
            ))
            all_models = idx.get_all()
            assert len(all_models) == 2
            names = {m.name for m in all_models}
            assert names == {"a", "b"}


class TestModelManager:
    """测试模型管理器主类"""

    def _make_project_root(self):
        """创建临时项目目录结构"""
        tmpdir = tempfile.mkdtemp()
        model_dir = Path(tmpdir) / "data" / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        for mt in ModelType:
            (model_dir / mt.value).mkdir(exist_ok=True)
        return tmpdir

    def teardown_method(self, method):
        """清理临时目录"""
        # 注意：tmpdir 在 setup 中创建，这里不删除（由 setup 管理）
        pass

    def test_init_with_project_root(self):
        """测试初始化（project_root 参数）"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            assert mm.model_root.exists()
            assert "data" in str(mm.model_root)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_init_default_root(self):
        """测试默认初始化（使用项目根目录）"""
        mm = ModelManager()
        assert mm.model_root is not None
        assert mm.model_root.exists()

    def test_register_model_file(self):
        """测试注册模型文件"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            # 创建测试文件
            test_file = mm.model_root / "checkpoints" / "test_model.safetensors"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_bytes(b"fake model data")

            meta = mm.register_model_file(test_file, ModelType.CHECKPOINT)
            assert meta is not None
            assert meta.name == "test_model"
            assert meta.model_type == ModelType.CHECKPOINT
            assert meta.file_size_bytes > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_model(self):
        """测试按名称获取模型"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            test_file = mm.model_root / "checkpoints" / "my_model.safetensors"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_bytes(b"data")
            mm.register_model_file(test_file, ModelType.CHECKPOINT)

            retrieved = mm.get_model("my_model")
            assert retrieved is not None
            assert retrieved.name == "my_model"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_models_by_type(self):
        """测试按类型查询模型"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            # 注册多个 CHECKPOINT
            for i in range(3):
                f = mm.model_root / "checkpoints" / f"ckpt{i}.safetensors"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"data")
                mm.register_model_file(f, ModelType.CHECKPOINT)
            # 注册 VAE
            vf = mm.model_root / "vae" / "vae.pt"
            vf.parent.mkdir(parents=True, exist_ok=True)
            vf.write_bytes(b"data")
            mm.register_model_file(vf, ModelType.VAE)

            ckpts = mm.get_models_by_type(ModelType.CHECKPOINT)
            assert len(ckpts) == 3
            vaes = mm.get_models_by_type(ModelType.VAE)
            assert len(vaes) == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_model_counts(self):
        """测试模型计数"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            f = mm.model_root / "checkpoints" / "a.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            mm.register_model_file(f, ModelType.CHECKPOINT)

            counts = mm.get_model_counts()
            assert counts.get("checkpoints", 0) == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_remove_model_index(self):
        """测试删除索引"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            f = mm.model_root / "checkpoints" / "remove_me.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            mm.register_model_file(f, ModelType.CHECKPOINT)
            assert mm.get_model("remove_me") is not None

            assert mm.remove_model_index("remove_me") is True
            assert mm.get_model("remove_me") is None
            # 重复删除返回 False
            assert mm.remove_model_index("remove_me") is False
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_storage_stats(self):
        """测试存储统计"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            stats = mm.get_storage_stats()
            assert "total_bytes" in stats
            assert "total_mb" in stats
            assert "file_count" in stats
            assert "indexed_count" in stats
            assert "type_counts" in stats
            assert stats["file_count"] >= 0
            assert stats["indexed_count"] == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_index_persistence(self):
        """测试索引持久化（重建管理器后仍存在）"""
        tmpdir = self._make_project_root()
        try:
            mm1 = ModelManager(project_root=tmpdir)
            f = mm1.model_root / "checkpoints" / "persistent.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            mm1.register_model_file(f, ModelType.CHECKPOINT)
            del mm1

            # 重建管理器（从同一目录加载索引）
            mm2 = ModelManager(project_root=tmpdir)
            retrieved = mm2.get_model("persistent")
            assert retrieved is not None
            assert retrieved.name == "persistent"
            assert retrieved.model_type == ModelType.CHECKPOINT
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_scan_and_index(self):
        """测试扫描目录并建立索引"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            # 手动创建模型文件
            f1 = mm.model_root / "checkpoints" / "scan_test.safetensors"
            f1.parent.mkdir(parents=True, exist_ok=True)
            f1.write_bytes(b"scan data")
            f2 = mm.model_root / "vae" / "scan_vae.pt"
            f2.parent.mkdir(parents=True, exist_ok=True)
            f2.write_bytes(b"scan vae")

            new_count = mm.scan_and_index(force=True)
            assert new_count >= 2

            all_models = mm.get_all_models()
            names = {m.name for m in all_models}
            assert "scan_test" in names
            assert "scan_vae" in names
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_verify_model(self):
        """测试模型完整性验证"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            f = mm.model_root / "checkpoints" / "verify_test.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"verify data")
            meta = mm.register_model_file(f, ModelType.CHECKPOINT)
            assert meta is not None
            # register_model_file 已计算 SHA256 并验证
            assert meta.sha256_hash != ""
            assert mm.verify_model("verify_test") is True
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_verify_model_missing(self):
        """测试缺失模型的验证"""
        tmpdir = self._make_project_root()
        try:
            mm = ModelManager(project_root=tmpdir)
            f = mm.model_root / "checkpoints" / "missing_test.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            meta = mm.register_model_file(f, ModelType.CHECKPOINT)
            # 删除实际文件
            f.unlink()
            # 验证应返回 False
            assert mm.verify_model("missing_test") is False
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestModelScanner:
    """测试模型扫描器"""

    def test_scan_empty_directory(self):
        """扫描空目录返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = ModelScanner(Path(tmpdir))
            result = scanner.scan_by_type(ModelType.CHECKPOINT)
            assert result == []

    def test_scan_with_files(self):
        """扫描包含模型文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            ckpt_dir = model_dir / "checkpoints"
            ckpt_dir.mkdir()
            (ckpt_dir / "model1.safetensors").write_bytes(b"data")
            (ckpt_dir / "model2.ckpt").write_bytes(b"data")
            (ckpt_dir / ".hidden").write_bytes(b"hidden")  # 应被排除

            scanner = ModelScanner(model_dir)
            results = scanner.scan_by_type(ModelType.CHECKPOINT)
            names = {r.name for r in results}
            assert "model1.safetensors" in names
            assert "model2.ckpt" in names
            assert ".hidden" not in names

    def test_scan_nonexistent_type(self):
        """扫描不存在的类型目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = ModelScanner(Path(tmpdir))
            result = scanner.scan_by_type(ModelType.IPADAPTER)
            assert result == []


class TestModelVerifier:
    """测试模型校验器"""

    def test_calculate_sha256(self):
        """测试 SHA256 计算"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            f.flush()
            hash_val = ModelVerifier.calculate_sha256(Path(f.name))
            assert hash_val is not None
            assert len(hash_val) == 64  # SHA256 hex length
        import os
        os.unlink(f.name)

    def test_verify_match(self):
        """测试校验匹配"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data")
            f.flush()
            expected = ModelVerifier.calculate_sha256(Path(f.name))
            assert ModelVerifier.verify(Path(f.name), expected) is True
        import os
        os.unlink(f.name)

    def test_verify_mismatch(self):
        """测试校验不匹配"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data")
            f.flush()
            assert ModelVerifier.verify(Path(f.name), "wrong_hash") is False
        import os
        os.unlink(f.name)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
