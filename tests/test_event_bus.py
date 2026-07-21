"""
事件总线测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.event_bus import EventBus, Event


class TestEventBus:
    """测试事件总线"""

    def setup_method(self):
        """每次测试前创建新的事件总线"""
        self.bus = EventBus()
        self.received_events = []

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        def handler(event):
            self.received_events.append(event)

        self.bus.subscribe("test", "hello", handler)
        event = Event("test", "hello", {"key": "value"})
        count = self.bus.publish(event)

        assert count == 1
        assert len(self.received_events) == 1
        assert self.received_events[0].data["key"] == "value"

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        received = []

        def handler1(event):
            received.append("h1")

        def handler2(event):
            received.append("h2")

        self.bus.subscribe("test", "multi", handler1)
        self.bus.subscribe("test", "multi", handler2)

        count = self.bus.publish(Event("test", "multi"))
        assert count == 2
        assert received == ["h1", "h2"]

    def test_once_subscription(self):
        """测试一次性订阅"""
        count = [0]

        def handler(event):
            count[0] += 1

        self.bus.subscribe("test", "once", handler, once=True)

        # 第一次发布
        self.bus.publish(Event("test", "once"))
        assert count[0] == 1

        # 第二次发布（一次性订阅不应再触发）
        self.bus.publish(Event("test", "once"))
        assert count[0] == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        received = []

        def handler(event):
            received.append(event)

        self.bus.subscribe("test", "unsubscribe", handler)
        self.bus.unsubscribe("test", "unsubscribe", handler)

        count = self.bus.publish(Event("test", "unsubscribe"))
        assert count == 0
        assert len(received) == 0

    def test_simple_publish(self):
        """测试简化版发布"""
        received = []

        def handler(event):
            received.append(event.name)

        self.bus.subscribe("simple", "test", handler)
        count = self.bus.publish_simple("simple", "test", {"data": 123})

        assert count == 1
        assert received == ["test"]

    def test_get_subscribers(self):
        """测试获取订阅者数量"""
        def handler(event):
            pass

        self.bus.subscribe("test", "count", handler)
        assert self.bus.get_subscribers("test", "count") == 1
        assert self.bus.get_subscribers("test", "nonexistent") == 0

    def test_clear(self):
        """测试清除所有订阅"""
        def handler(event):
            pass

        self.bus.subscribe("test", "clear", handler)
        self.bus.clear()
        assert self.bus.get_subscribers("test", "clear") == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
