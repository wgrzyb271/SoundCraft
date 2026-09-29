"""Pamięć powiadomień callback i oczekujących połączeń WebSocket."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any


class CompletionRegistry:
    def __init__(self, retention_s: float = 7200.0):
        self.retention_s = retention_s
        self._completed: dict[str, tuple[float, dict[str, Any]]] = {}
        self._waiters: dict[str, set[asyncio.Event]] = defaultdict(set)
        self._lock = asyncio.Lock()

    def _prune(self, now: float) -> None:
        expired = [key for key, (stamp, _) in self._completed.items() if now - stamp > self.retention_s]
        for key in expired:
            self._completed.pop(key, None)

    async def mark_completed(self, request_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            self._prune(time.monotonic())
            self._completed[request_id] = (time.monotonic(), dict(payload))
            for event in self._waiters.pop(request_id, set()):
                event.set()

    async def wait(self, request_id: str, timeout_s: float) -> dict[str, Any] | None:
        event = asyncio.Event()
        async with self._lock:
            self._prune(time.monotonic())
            completed = self._completed.get(request_id)
            if completed is not None:
                return dict(completed[1])
            self._waiters[request_id].add(event)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_s)
            async with self._lock:
                completed = self._completed.get(request_id)
                return dict(completed[1]) if completed is not None else None
        except asyncio.TimeoutError:
            return None
        finally:
            async with self._lock:
                waiters = self._waiters.get(request_id)
                if waiters is not None:
                    waiters.discard(event)
                    if not waiters:
                        self._waiters.pop(request_id, None)


completion_registry = CompletionRegistry()
