"""
Shadow CLI - Event System (SSE-based real-time notifications)
Broadcasts player/guild events to connected SSE clients.

Usage:
    from events import event_bus, broadcast

    broadcast("level_up", {"level": 10, "title": "D 级猎人"})
"""

import json
import threading
import time
from datetime import datetime
from queue import Queue, Full

# ── Configuration ──────────────────────────────────────────────────────────

MAX_QUEUE_SIZE = 100       # Max events buffered per client
CLEANUP_INTERVAL = 30      # Seconds between stale client cleanup
HEARTBEAT_INTERVAL = 15    # Seconds between heartbeat messages

# ── Event Bus ──────────────────────────────────────────────────────────────

class EventBus:
    """Thread-safe event bus with SSE client support."""

    def __init__(self):
        self._clients: dict[str, dict] = {}  # client_id -> {"queue": Queue, "subscribed_at": float, "types": set}
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._max_history = 200
        self._next_id = 0

    def subscribe(self, client_id: str, event_types: list[str] | None = None) -> Queue:
        """Subscribe to events. Returns a queue that will receive event data."""
        queue: Queue = Queue(maxsize=MAX_QUEUE_SIZE)
        with self._lock:
            self._clients[client_id] = {
                "queue": queue,
                "subscribed_at": time.time(),
                "types": set(event_types) if event_types else None,
            }
        return queue

    def unsubscribe(self, client_id: str) -> None:
        """Remove a client subscription."""
        with self._lock:
            self._clients.pop(client_id, None)

    def broadcast(self, event_type: str, data: dict, source: str = "") -> str:
        """Broadcast an event to all subscribed clients. Returns event_id."""
        event_id = str(self._next_id)
        self._next_id += 1

        event = {
            "id": event_id,
            "type": event_type,
            "data": data,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }

        # Add to history
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # Push to client queues
        dead_clients = []
        with self._lock:
            for cid, client in self._clients.items():
                # Filter by event type if subscription has type filter
                if client["types"] and event_type not in client["types"]:
                    continue
                try:
                    client["queue"].put_nowait(event)
                except Full:
                    dead_clients.append(cid)

        # Remove overloaded clients
        with self._lock:
            for cid in dead_clients:
                self._clients.pop(cid, None)

        return event_id

    def get_history(self, event_types: list[str] | None = None, since_id: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent event history."""
        with self._lock:
            events = list(self._history)

        # Filter by since_id
        if since_id:
            since_idx = None
            for i, e in enumerate(events):
                if e["id"] == since_id:
                    since_idx = i + 1
                    break
            if since_idx is not None:
                events = events[since_idx:]

        # Filter by type
        if event_types:
            events = [e for e in events if e["type"] in event_types]

        return events[-limit:]

    def cleanup_stale(self, max_age: float = 300) -> int:
        """Remove clients that haven't been active recently. Returns count removed."""
        now = time.time()
        removed = 0
        with self._lock:
            stale = [
                cid for cid, client in self._clients.items()
                if now - client["subscribed_at"] > max_age
            ]
            for cid in stale:
                self._clients.pop(cid, None)
                removed += 1
        return removed

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)


# ── Global Instance ────────────────────────────────────────────────────────

event_bus = EventBus()

# Convenience function
broadcast = event_bus.broadcast

# ── Helper: Format event for SSE ──────────────────────────────────────────

def format_sse(event: dict) -> str:
    """Format an event as SSE data string."""
    lines = []
    lines.append(f"id: {event['id']}")
    lines.append(f"event: {event['type']}")
    lines.append(f"data: {json.dumps(event['data'], ensure_ascii=False)}")
    if "timestamp" in event:
        lines.append(f"retry: 3000")
    lines.append("")  # Empty line terminates the event
    lines.append("")
    return "\n".join(lines)


def format_heartbeat() -> str:
    """Format an SSE keepalive comment."""
    return ": heartbeat\n\n"
