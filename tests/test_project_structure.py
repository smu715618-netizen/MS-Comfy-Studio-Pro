"""
基础测试 - 验证项目结构完整性
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestProjectStructure:
    """测试项目目录结构"""

    def test_root_files_exist(self):
        """测试根目录文件存在"""
        root = Path(__file__).parent.parent
        required_files = [
            "README.md",
            "LICENSE",
            "pyproject.toml",
            "requirements.txt",
            "requirements-xpu.txt",
            "setup.bat",
            "setup.ps1",
            "run_comfy.bat",
            "run_launcher.bat",
            "uninstall.bat",
        ]
        for f in required_files:
            assert (root / f).exists(), f"缺少文件: {f}"

    def test_config_files_exist(self):
        """测试配置文件存在"""
        root = Path(__file__).parent.parent
        required_configs = [
            "configs/default.yaml",
            "configs/xpu.yaml",
            "configs/locales/zh-CN.json",
            "configs/locales/en-US.json",
        ]
        for f in required_configs:
            assert (root / f).exists(), f"缺少配置: {f}"

    def test_src_modules_exist(self):
        """测试源代码模块存在"""
        root = Path(__file__).parent.parent
        required_modules = [
            "src/__init__.py",
            "src/__version__.py",
            "src/cli.py",
            "src/logger.py",
            "src/config_manager.py",
            "src/i18n.py",
            "src/gpu_detector.py",
            "src/env_manager.py",
            "src/models.py",
            "src/nodes.py",
            "src/workflows.py",
            "src/plugins.py",
            "src/updater.py",
            "src/launcher.py",
            "src/health_check.py",
        ]
        for f in required_modules:
            assert (root / f).exists(), f"缺少模块: {f}"

    def test_core_modules_exist(self):
        """测试核心模块存在"""
        root = Path(__file__).parent.parent
        required_core = [
            "src/core/__init__.py",
            "src/core/base.py",
            "src/core/event_bus.py",
            "src/core/dependency.py",
        ]
        for f in required_core:
            assert (root / f).exists(), f"缺少核心模块: {f}"

    def test_gui_modules_exist(self):
        """测试 GUI 模块存在"""
        root = Path(__file__).parent.parent
        required_gui = [
            "src/gui/__init__.py",
            "src/gui/app.py",
            "src/gui/main_window.py",
            "src/gui/styles.qss",
            "src/gui/widgets/__init__.py",
            "src/gui/widgets/console_widget.py",
            "src/gui/widgets/status_bar.py",
        ]
        for f in required_gui:
            assert (root / f).exists(), f"缺少 GUI 模块: {f}"

    def test_data_dirs_exist(self):
        """测试数据目录存在"""
        root = Path(__file__).parent.parent
        required_dirs = [
            "data/models/checkpoints",
            "data/models/vae",
            "data/models/clip",
            "data/models/unet",
            "data/models/lora",
            "data/models/controlnet",
            "data/models/upscale",
            "data/models/embedding",
            "data/workflows/builtins",
            "data/workflows/user",
            "data/workflows/templates",
            "data/plugins",
            "data/logs",
        ]
        for d in required_dirs:
            assert (root / d).is_dir(), f"缺少目录: {d}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
