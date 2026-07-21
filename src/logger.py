"""
日志系统模块

提供统一的日志管理功能：
- 多级别日志 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- 文件日志 (自动轮转)
- 控制台日志 (彩色输出)
- 结构化日志格式
- 线程安全
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器，用于控制台输出"""

    # ANSI 颜色代码
    COLORS = {
        logging.DEBUG: "\033[36m",      # 青色
        logging.INFO: "\033[32m",       # 绿色
        logging.WARNING: "\033[33m",    # 黄色
        logging.ERROR: "\033[31m",      # 红色
        logging.CRITICAL: "\033[35m",   # 紫色
    }
    RESET = "\033[0m"

    def __init__(self, fmt: Optional[str] = None):
        super().__init__(fmt or self._default_format)

    @property
    def _default_format(self):
        return "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        """添加颜色到日志级别"""
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class LoggerManager:
    """
    日志管理器

    单例模式，管理所有模块的日志记录器。
    支持控制台输出和文件轮转输出。
    """

    _instance = None
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._config = {}

    def setup(
        self,
        log_level: str = "INFO",
        log_dir: str = "data/logs",
        max_size_mb: int = 10,
        backup_count: int = 5,
        console_output: bool = True,
        log_format: Optional[str] = None,
    ):
        """
        初始化日志系统

        Args:
            log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            log_dir: 日志文件目录
            max_size_mb: 单个日志文件最大大小 (MB)
            backup_count: 保留的备份文件数量
            console_output: 是否输出到控制台
            log_format: 自定义日志格式字符串
        """
        self._config = {
            "log_level": log_level,
            "log_dir": log_dir,
            "max_size_mb": max_size_mb,
            "backup_count": backup_count,
            "console_output": console_output,
            "log_format": log_format,
        }

        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)

        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # 清除已有的 handler
        root_logger.handlers.clear()

        # 添加控制台 handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ColoredFormatter(log_format))
            root_logger.addHandler(console_handler)

        # 添加文件 handler (带轮转)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"mcsp_{timestamp}.log")

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(
            log_format or "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(file_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        获取命名日志记录器

        Args:
            name: 日志记录器名称 (通常为模块名)

        Returns:
            logging.Logger 实例
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        self._loggers[name] = logger
        return logger

    def reset(self):
        """重置日志系统配置"""
        self._loggers.clear()
        self._config.clear()
        logging.getLogger().handlers.clear()


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """
    快捷函数：获取命名日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger 实例
    """
    return _logger_manager.get_logger(name)


def setup_logging(**kwargs):
    """
    快捷函数：初始化日志系统

    用法:
        setup_logging(log_level="DEBUG", console_output=True)
    """
    _logger_manager.setup(**kwargs)


# 模块级便捷函数
def debug(name: str, message: str):
    """记录 DEBUG 级别日志"""
    get_logger(name).debug(message)


def info(name: str, message: str):
    """记录 INFO 级别日志"""
    get_logger(name).info(message)


def warning(name: str, message: str):
    """记录 WARNING 级别日志"""
    get_logger(name).warning(message)


def error(name: str, message: str):
    """记录 ERROR 级别日志"""
    get_logger(name).error(message)


def critical(name: str, message: str):
    """记录 CRITICAL 级别日志"""
    get_logger(name).critical(message)
