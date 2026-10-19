"""
In-process event hub for live call status/transcript streaming.

Sync producers (FastAPI request handlers, workers) publish here; async consumers
(the WebSocket endpoint) subscribe. Swap for Redis pub/sub for multi-worker
deployments — the interface is intentionally tiny.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_HISTORY = 500


class EventHub:
    """Fan-out of per-call events to any number of async subscribers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._history: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=_MAX_HISTORY))

    # ------------------------------------------------------------------ #
    def publish(self, call_id: str, event: Dict[str, Any]) -> None:
        """Publish an event. Safe to call from sync or async code."""
        payload = {"call_id": call_id, "ts": time.time(), **event}
        with self._lock:
            self._history[call_id].append(payload)
            queues = list(self._subscribers.get(call_id, []))

        for q in queues:
            loop = getattr(q, "_sf_loop", None)
            try:
                if loop is not None and loop.is_running():
                    loop.call_soon_threadsafe(q.put_nowait, payload)
                else:
                    q.put_nowait(payload)
            except Exception:  # pragma: no cover - slow/broken consumer
                logger.debug("Dropping event for %s: queue unavailable", call_id)

    def history(self, call_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history.get(call_id, []))

    # ------------------------------------------------------------------ #
    def subscribe(self, call_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        try:
            q._sf_loop = asyncio.get_running_loop()  # type: ignore[attr-defined]
        except RuntimeError:
            q._sf_loop = None  # type: ignore[attr-defined]
        with self._lock:
            self._subscribers[call_id].append(q)
        return q

    def unsubscribe(self, call_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            if call_id in self._subscribers and q in self._subscribers[call_id]:
                self._subscribers[call_id].remove(q)
            if call_id in self._subscribers and not self._subscribers[call_id]:
                self._subscribers.pop(call_id, None)

    def clear(self, call_id: Optional[str] = None) -> None:
        with self._lock:
            if call_id is None:
                self._subscribers.clear()
                self._history.clear()
            else:
                self._subscribers.pop(call_id, None)
                self._history.pop(call_id, None)


# Process-wide default hub.
event_hub = EventHub()
