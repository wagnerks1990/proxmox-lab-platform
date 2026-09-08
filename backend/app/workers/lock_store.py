from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock
import uuid

from redis import Redis


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


class RedisWorkerLockStore(WorkerLockStore):
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)
        self._tokens: dict[str, str] = {}

    def acquire(self, name: str, ttl_seconds: int = 60) -> bool:
        token = uuid.uuid4().hex
        acquired = bool(self.client.set(f'plp:worker-lock:{name}', token, nx=True, ex=ttl_seconds))
        if acquired:
            self._tokens[name] = token
        return acquired

    def release(self, name: str) -> None:
        token = self._tokens.pop(name, None)
        if token:
            self.client.eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, f'plp:worker-lock:{name}', token)


def build_lock_store(backend: str) -> WorkerLockStore:
    if backend == 'memory':
        return InMemoryWorkerLockStore()
    if backend == 'redis':
        from app.core.config import settings
        return RedisWorkerLockStore(settings.redis_url)
    raise ValueError(f'Unsupported worker lock backend: {backend}')
