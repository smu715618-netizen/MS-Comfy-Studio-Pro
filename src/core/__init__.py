# 核心框架包

"""
核心框架模块

提供基础架构组件：
- BaseComponent: 所有组件的基类
- EventBus: 事件总线（发布/订阅模式）
- DependencyContainer: 简单的依赖注入容器
"""

from src.core.base import BaseComponent
from src.core.event_bus import EventBus
from src.core.dependency import DependencyContainer

__all__ = ["BaseComponent", "EventBus", "DependencyContainer"]
