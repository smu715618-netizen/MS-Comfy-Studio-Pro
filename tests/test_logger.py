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
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level="DEBUG",
                log_dir=tmpdir,
                console_output=False,
            )
            logger = get_logger("test")
            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.DEBUG

    def test_get_logger(self):
        """测试获取日志记录器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, console_output=False)
            logger = get_logger("test_module")
            assert logger.name == "test_module"

    def test_log_levels(self):
        """测试各级别日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_level="DEBUG", log_dir=tmpdir, console_output=False)
            logger = get_logger("test_levels")

            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")
            logger.critical("critical message")

            # 验证日志文件已创建
            import os
            files = os.listdir(tmpdir)
            assert len(files) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
