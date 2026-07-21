"""
事件总线

实现发布/订阅模式的事件系统。
用于组件间通信，解耦各模块。

事件类型：
- system: 系统事件（启动、停止、错误）
- model: 模型事件（下载、安装、验证）
- node: 节点事件（安装、更新、启用/禁用）
- workflow: 工作流事件（保存、加载、导入、导出）
- update: 更新事件（检查、下载、安装）
- gpu: GPU 事件（检测、状态变化）
"""

import threading
from typing import Callable, Dict, List, Any, Optional
from collections import defaultdict
from src.logger import get_logger

logger = get_logger("event_bus")


class Event:
    """事件对象"""

    def __init__(self, event_type: str, name: str, data: Optional[dict] = None):
        self.type = event_type
        self.name = name
        self.data = data or {}
        self._handlers_called: List[Callable] = []

    @property
    def full_name(self) -> str:
        """完整事件名: type.name"""
        return f"{self.type}.{self.name}"

    def __repr__(self):
        return f"Event(type={self.type}, name={self.name}, data_keys={list(self.data.keys())})"


class EventHandler:
    """事件处理器包装"""

    def __init__(self, callback: Callable, once: bool = False):
        self.callback = callback
        self.once = once
        self.active = True


class EventBus:
    """
    事件总线

    线程安全的发布/订阅事件系统。
    支持一次性订阅和持续订阅。
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(
        self,
        event_type: str,
        event_name: str,
        callback: Callable,
        once: bool = False,
    ):
        """
        订阅事件

        Args:
            event_type: 事件类型
            event_name: 事件名称
            callback: 回调函数 (event: Event) -> None
            once: 是否只触发一次
        """
        full_name = f"{event_type}.{event_name}"
        handler = EventHandler(callback, once=once)

        with self._lock:
            self._handlers[full_name].append(handler)

        logger.debug(f"已订阅事件: {full_name}")

    def unsubscribe(self, event_type: str, event_name: str, callback: Callable):
        """
        取消订阅

        Args:
            event_type: 事件类型
            event_name: 事件名称
            callback: 要移除的回调函数
        """
        full_name = f"{event_type}.{event_name}"
        with self._lock:
            self._handlers[full_name] = [
                h for h in self._handlers[full_name]
                if h.callback is not callback
            ]
            if not self._handlers[full_name]:
                del self._handlers[full_name]

        logger.debug(f"已取消订阅: {full_name}")

    def publish(self, event: Event) -> int:
        """
        发布事件

        Args:
            event: 事件对象

        Returns:
            被调用的处理器数量
        """
        full_name = event.full_name
        handlers_to_call = []
        handlers_to_remove = []

        with self._lock:
            if full_name in self._handlers:
                handlers_to_call = list(self._handlers[full_name])

        count = 0
        for handler in handlers_to_call:
            if not handler.active:
                continue

            try:
                handler.callback(event)
                count += 1
                event._handlers_called.append(handler.callback)

                if handler.once:
                    handlers_to_remove.append(handler)
            except Exception as e:
                logger.error(f"事件处理器异常 {full_name}: {e}")

        # 移除一次性处理器
        with self._lock:
            for handler in handlers_to_remove:
                if full_name in self._handlers:
                    self._handlers[full_name] = [
                        h for h in self._handlers[full_name] if h is not handler
                    ]

        return count

    def publish_simple(
        self,
        event_type: str,
        event_name: str,
        data: Optional[dict] = None,
    ) -> int:
        """
        简化版发布

        Args:
            event_type: 事件类型
            event_name: 事件名称
            data: 事件数据

        Returns:
            被调用的处理器数量
        """
        event = Event(event_type, event_name, data)
        return self.publish(event)

    def get_subscribers(self, event_type: str, event_name: str) -> int:
        """获取事件的订阅者数量"""
        full_name = f"{event_type}.{event_name}"
        with self._lock:
            return len(self._handlers.get(full_name, []))

    def clear(self):
        """清除所有订阅"""
        with self._lock:
            self._handlers.clear()

    def reset_once_handlers(self):
        """重置所有一次性处理器为活跃状态"""
        with self._lock:
            for handlers in self._handlers.values():
                for handler in handlers:
                    if handler.once:
                        handler.active = True
