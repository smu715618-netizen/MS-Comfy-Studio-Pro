"""
日志系统测试
"""

import sys
import tempfile
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import LoggerManager, setup_logging, get_logger


class TestLoggerManager:
    """测试日志管理器"""

    def test_singleton(self):
        """测试单例模式"""
        lm1 = LoggerManager()
        lm2 = LoggerManager()
        assert lm1 is lm2

    def test_setup(self):
        """测试日志初始化"""
        import logging as _logging
        LoggerManager._instance = None
        _tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(log_level="DEBUG", log_dir=_tmpdir, console_output=False)
            logger = get_logger("test_logger_v2")
            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.DEBUG
        finally:
            _logging.getLogger().handlers.clear()
            _logging.shutdown()
            import shutil
            shutil.rmtree(_tmpdir, ignore_errors=True)

    def test_get_logger(self):
        """测试获取日志记录器"""
        import logging as _logging
        LoggerManager._instance = None
        _tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(log_dir=_tmpdir, console_output=False)
            logger = get_logger("test_module_v2")
            assert logger.name == "test_module_v2"
        finally:
            _logging.getLogger().handlers.clear()
            _logging.shutdown()
            import shutil
            shutil.rmtree(_tmpdir, ignore_errors=True)

    def test_log_levels(self):
        """测试各级别日志"""
        import logging as _logging
        LoggerManager._instance = None
        _tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(log_level="DEBUG", log_dir=_tmpdir, console_output=False)
            logger = get_logger("test_levels_v2")
            logger.debug("debug")
            logger.info("info")
            logger.warning("warning")
            logger.error("error")
            logger.critical("critical")
            import os
            files = os.listdir(_tmpdir)
            assert len(files) > 0
        finally:
            _logging.getLogger().handlers.clear()
            _logging.shutdown()
            import shutil
            shutil.rmtree(_tmpdir, ignore_errors=True)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
