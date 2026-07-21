"""
依赖注入容器

简单的依赖注入框架，支持：
- 注册单例
- 注册工厂函数
- 按类型解析依赖
- 生命周期管理
"""

from typing import Any, Callable, Dict, Optional, Type
from src.logger import get_logger

logger = get_logger("dependency")


class DependencyContainer:
    """
    依赖注入容器

    管理应用中各组件的依赖关系。
    """

    def __init__(self):
        self._registry: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, name: str, instance: Any, singleton: bool = False):
        """
        注册一个实例

        Args:
            name: 注册名
            instance: 实例对象
            singleton: 是否作为单例
        """
        if singleton:
            self._singletons[name] = instance
        else:
            self._registry[name] = instance
        logger.debug(f"已注册: {name}")

    def register_factory(self, name: str, factory: Callable):
        """
        注册一个工厂函数

        Args:
            name: 注册名
            factory: 返回实例的工厂函数
        """
        self._factories[name] = factory
        logger.debug(f"已注册工厂: {name}")

    def resolve(self, name: str) -> Any:
        """
        解析依赖

        Args:
            name: 注册名

        Returns:
            注册的实例
        """
        # 检查单例
        if name in self._singletons:
            return self._singletons[name]

        # 检查注册
        if name in self._registry:
            return self._registry[name]

        # 检查工厂
        if name in self._factories:
            instance = self._factories[name]()
            self._registry[name] = instance
            return instance

        raise KeyError(f"未注册的依赖: {name}")

    def has(self, name: str) -> bool:
        """检查是否已注册"""
        return (
            name in self._registry
            or name in self._singletons
            or name in self._factories
        )

    def unregister(self, name: str):
        """注销依赖"""
        self._registry.pop(name, None)
        self._factories.pop(name, None)
        self._singletons.pop(name, None)
        logger.debug(f"已注销: {name}")

    def get_all(self) -> Dict[str, Any]:
        """获取所有已注册的依赖"""
        result = dict(self._registry)
        result.update(self._singletons)
        return result
