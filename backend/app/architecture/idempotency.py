from __future__ import annotations

from threading import Lock


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._keys: set[str] = set()
        self._lock = Lock()

    def reserve(self, key: str) -> bool:
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._keys.discard(key)


store = InMemoryIdempotencyStore()
