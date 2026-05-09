"""
Shadow CLI - Events System Tests
Tests for SSE event bus.
"""

import time
import threading
import pytest
from events import EventBus, format_sse, format_heartbeat


class TestEventBus:
    """Test event bus core functionality."""

    def test_subscribe_and_broadcast(self):
        bus = EventBus()
        queue = bus.subscribe("client1")

        event_id = bus.broadcast("test_event", {"key": "value"})
        assert event_id == "0"

        event = queue.get(timeout=1)
        assert event["type"] == "test_event"
        assert event["data"] == {"key": "value"}
        assert event["id"] == "0"

    def test_type_filtering(self):
        bus = EventBus()
        queue = bus.subscribe("client1", event_types=["type_a"])

        bus.broadcast("type_a", {"msg": "should receive"})
        bus.broadcast("type_b", {"msg": "should not receive"})

        event = queue.get(timeout=1)
        assert event["type"] == "type_a"

        with pytest.raises(Exception):  # Queue empty
            queue.get(timeout=0.1)

    def test_multiple_subscribers(self):
        bus = EventBus()
        queue1 = bus.subscribe("client1")
        queue2 = bus.subscribe("client2")

        bus.broadcast("multi", {"data": 42})

        event1 = queue1.get(timeout=1)
        event2 = queue2.get(timeout=1)
        assert event1["data"]["data"] == 42
        assert event2["data"]["data"] == 42

    def test_unsubscribe(self):
        bus = EventBus()
        queue = bus.subscribe("client1")
        bus.unsubscribe("client1")

        bus.broadcast("after_unsub", {"msg": "ignored"})

        with pytest.raises(Exception):
            queue.get(timeout=0.2)

    def test_client_count(self):
        bus = EventBus()
        assert bus.client_count() == 0

        bus.subscribe("c1")
        assert bus.client_count() == 1

        bus.subscribe("c2")
        assert bus.client_count() == 2

        bus.unsubscribe("c1")
        assert bus.client_count() == 1

    def test_event_history(self):
        bus = EventBus()
        bus.subscribe("client1")

        id0 = bus.broadcast("evt1", {"n": 1})
        id1 = bus.broadcast("evt2", {"n": 2})
        id2 = bus.broadcast("evt3", {"n": 3})

        history = bus.get_history()
        assert len(history) == 3

        # Since id1 should return events after id1
        history = bus.get_history(since_id=id1)
        assert len(history) == 1
        assert history[0]["id"] == id2

    def test_history_type_filter(self):
        bus = EventBus()
        bus.subscribe("client1")

        bus.broadcast("chat", {"msg": "hello"})
        bus.broadcast("game", {"score": 100})
        bus.broadcast("chat", {"msg": "world"})
        bus.broadcast("guild", {"task": "done"})

        chat_history = bus.get_history(event_types=["chat"])
        assert len(chat_history) == 2
        assert all(e["type"] == "chat" for e in chat_history)

    def test_history_limit(self):
        bus = EventBus()
        bus.subscribe("client1")

        for i in range(50):
            bus.broadcast("many", {"i": i})

        history = bus.get_history(limit=10)
        assert len(history) == 10

    def test_broadcast_source(self):
        bus = EventBus()
        queue = bus.subscribe("client1")

        bus.broadcast("test", {}, source="api:user123")
        event = queue.get(timeout=1)
        assert event["source"] == "api:user123"


class TestEventCleanup:
    """Test event bus cleanup functionality."""

    def test_cleanup_stale_clients(self):
        bus = EventBus()
        bus.subscribe("active_client")

        # Simulate stale subscription by modifying timestamp directly
        with bus._lock:
            bus._clients["stale_client"] = {
                "queue": None,
                "subscribed_at": time.time() - 600,
                "types": None,
            }

        removed = bus.cleanup_stale(max_age=300)
        assert removed == 1
        assert bus.client_count() == 1


class TestSSEFormatting:
    """Test SSE message formatting."""

    def test_format_sse(self):
        event = {
            "id": "42",
            "type": "level_up",
            "data": {"level": 10, "title": "D 级猎人"},
            "timestamp": "2026-05-09T12:00:00",
        }
        sse = format_sse(event)
        assert "id: 42" in sse
        assert "event: level_up" in sse
        assert "D 级猎人" in sse

    def test_format_heartbeat(self):
        hb = format_heartbeat()
        assert ": heartbeat" in hb


class TestThreadSafety:
    """Test event bus thread safety."""

    def test_concurrent_broadcast(self):
        bus = EventBus()
        queue = bus.subscribe("client1")

        def broadcast_many():
            for i in range(20):
                bus.broadcast("concurrent", {"i": i})

        threads = [threading.Thread(target=broadcast_many) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have received most events (queue max is 100, we broadcast 60)
        count = 0
        while True:
            try:
                queue.get(timeout=0.1)
                count += 1
            except Exception:
                break

        assert count == 60  # 3 threads * 20 events
