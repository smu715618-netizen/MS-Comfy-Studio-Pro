"""Integration test — MS Comfy Studio Pro

标准 pytest 测试结构。
所有测试在函数内部执行，无模块级代码。
动态获取项目根目录，禁止硬编码路径。
GPU 检测失败不影响其他测试。
"""

import sys
import tempfile
import logging
from pathlib import Path

# 动态获取项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.config_manager import ConfigManager, get_config
from src.logger import setup_logging, get_logger
from src.i18n import I18nManager
from src.gpu_detector import GPUDetector
from src.health_check import HealthChecker
from src.models import ModelManager, ModelType
from src.nodes import NodeManager
from src.workflows import WorkflowManager


class TestIntegration:
    """集成测试 — 核心模块端到端验证"""

    def test_config_manager(self):
        """测试配置加载和读取"""
        config = ConfigManager()
        assert config.get('app.name') == 'MS Comfy Studio Pro'
        assert config.get('gpu.device') == 'xpu'
        assert config.get('comfyui.port') == 8188
        assert config.get('paths.data_dir') == 'data'
        gc = get_config()
        assert gc.get('app.name') == 'MS Comfy Studio Pro'

    def test_logger_setup(self):
        """测试日志系统初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_level='DEBUG', log_dir=tmpdir, console_output=False)
            logger = get_logger('integration_test')
            assert isinstance(logger, logging.Logger)
            logger.info('test message')
            import os
            files = os.listdir(tmpdir)
            assert len(files) > 0

    def test_i18n(self):
        """测试国际化"""
        i18n = I18nManager()
        assert i18n.t('app.name') == 'MS Comfy Studio Pro'
        i18n.set_locale('en-US')
        assert i18n.t('app.name') == 'MS Comfy Studio Pro'

    def test_gpu_detector(self):
        """测试 GPU 检测（失败不影响其他测试）"""
        detector = GPUDetector()
        info = detector.detect()
        assert info is not None
        assert info.gpu_type is not None

    def test_gpu_detector_no_crash_on_nvidia_error(self):
        """测试 NVIDIA 检测失败时不崩溃"""
        detector = GPUDetector()
        info = detector._detect_nvidia()
        assert info is not None
        assert info.gpu_type.value == 'unknown' or info.name == ''

    def test_gpu_system_info(self):
        """测试系统信息获取"""
        detector = GPUDetector()
        sys_info = detector.get_system_info()
        assert sys_info is not None
        assert sys_info.python_version != ''
        assert sys_info.os_name != ''

    def test_health_checker(self):
        """测试健康检查"""
        hc = HealthChecker(project_root=str(_PROJECT_ROOT))
        summary = hc.get_summary()
        assert 'overall' in summary
        assert 'passed' in summary

    def test_model_manager(self):
        """测试模型管理器初始化"""
        mm = ModelManager(project_root=str(_PROJECT_ROOT))
        assert mm is not None
        stats = mm.get_storage_stats()
        assert 'total_bytes' in stats
        assert 'indexed_count' in stats

    def test_node_manager(self):
        """测试节点管理器初始化"""
        nm = NodeManager(project_root=str(_PROJECT_ROOT))
        assert nm is not None

    def test_workflow_manager(self):
        """测试工作流管理器初始化"""
        wm = WorkflowManager(workflows_dir=str(_PROJECT_ROOT / 'data' / 'workflows'))
        assert wm is not None
