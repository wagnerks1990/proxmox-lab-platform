from __future__ import annotations

import asyncio


class EventStream:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    async def publish(self, event: dict) -> None:
        dead = []
        for q in self._subs:
            try:
                q.put_nowait(event)
            except Exception:
                dead.append(q)
        for q in dead:
            self._subs.discard(q)


event_stream = EventStream()
