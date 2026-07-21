"""
配置管理测试
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager


class TestConfigManager:
    """测试配置管理器"""

    def test_default_config_loads(self):
        """测试默认配置加载"""
        config = ConfigManager()
        assert config.get("app.name") == "MS Comfy Studio Pro"
        assert config.get("app.version") == "0.1.0"
        assert config.get("comfyui.port") == 8188

    def test_gpu_config(self):
        """测试 GPU 配置"""
        config = ConfigManager()
        assert config.get("gpu.preferred_type") == "intel_xpu"
        assert config.get("gpu.device") == "xpu"

    def test_path_config(self):
        """测试路径配置"""
        config = ConfigManager()
        assert config.get("paths.data_dir") == "data"
        assert config.get("paths.models_dir") == "data/models"

    def test_set_and_get(self):
        """测试设置和获取配置值"""
        config = ConfigManager()
        config.set("test.key", "test_value")
        assert config.get("test.key") == "test_value"

    def test_default_value(self):
        """测试默认值"""
        config = ConfigManager()
        result = config.get("nonexistent.key", "default_val")
        assert result == "default_val"

    def test_section_access(self):
        """测试节访问"""
        config = ConfigManager()
        gpu_section = config.get_section("gpu")
        assert isinstance(gpu_section, dict)
        assert "preferred_type" in gpu_section

    def test_reload(self):
        """测试重新加载配置"""
        config = ConfigManager()
        initial = config.get("app.name")
        config.reload()
        assert config.get("app.name") == initial


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
