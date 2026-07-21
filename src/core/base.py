"""
组件基类

所有 MCSP 模块组件的抽象基类。
提供生命周期管理和配置访问。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.logger import get_logger
from src.config_manager import ConfigManager

logger = get_logger("core")


class BaseComponent(ABC):
    """
    组件基类

    所有 MCSP 模块都应继承此类，以获得：
    - 统一的生命周期管理 (initialize / shutdown)
    - 配置访问
    - 日志记录
    - 状态跟踪
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        初始化组件

        Args:
            config: 配置管理器实例
        """
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._initialized = False
        self._name = self.__class__.__name__

    @property
    def name(self) -> str:
        """组件名称"""
        return self._name

    @property
    def is_initialized(self) -> bool:
        """组件是否已初始化"""
        return self._initialized

    def initialize(self):
        """
        初始化组件（子类可重写）

        在组件使用前调用。
        """
        self._logger.info(f"正在初始化组件: {self._name}")
        self._do_initialize()
        self._initialized = True
        self._logger.info(f"组件初始化完成: {self._name}")

    def _do_initialize(self):
        """子类实现的初始化逻辑"""
        pass

    def shutdown(self):
        """
        关闭组件（子类可重写）

        释放资源，清理状态。
        """
        self._logger.info(f"正在关闭组件: {self._name}")
        self._do_shutdown()
        self._initialized = False
        self._logger.info(f"组件已关闭: {self._name}")

    def _do_shutdown(self):
        """子类实现的关闭逻辑"""
        pass

    def get_config(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key_path: 配置键路径
            default: 默认值

        Returns:
            配置值
        """
        if self._config:
            return self._config.get(key_path, default)
        return default

    def __repr__(self):
        status = "initialized" if self._initialized else "not initialized"
        return f"{self.__class__.__name__}(name={self._name}, status={status})"
