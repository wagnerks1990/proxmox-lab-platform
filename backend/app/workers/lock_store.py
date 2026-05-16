from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock


class WorkerLockStore(ABC):
    @abstractmethod
    def acquire(self, name: str, ttl_seconds: int = 60) -> bool:
        raise NotImplementedError

    @abstractmethod
    def release(self, name: str) -> None:
        raise NotImplementedError


class InMemoryWorkerLockStore(WorkerLockStore):
    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[str, int] = {}

    def acquire(self, name: str, ttl_seconds: int = 60) -> bool:
        now = int(datetime.now(timezone.utc).timestamp())
        with self._lock:
            self._entries = {k: v for k, v in self._entries.items() if v >= now}
            if name in self._entries:
                return False
            self._entries[name] = now + ttl_seconds
            return True

    def release(self, name: str) -> None:
        with self._lock:
            self._entries.pop(name, None)


def build_lock_store(backend: str) -> WorkerLockStore:
    if backend == 'memory':
        return InMemoryWorkerLockStore()
    if backend in {'redis', 'database'}:
        return InMemoryWorkerLockStore()
    raise ValueError(f'Unsupported worker lock backend: {backend}')
