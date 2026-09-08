from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock

from redis import Redis


class ReplayStore(ABC):
    @abstractmethod
    def mark_used(self, token_id: str, expires_at: int) -> bool:
        raise NotImplementedError


class InMemoryReplayStore(ReplayStore):
    def __init__(self) -> None:
        self._lock = Lock()
        self._used_until: dict[str, int] = {}

    def mark_used(self, token_id: str, expires_at: int) -> bool:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        with self._lock:
            self._used_until = {k: exp for k, exp in self._used_until.items() if exp >= now_ts}
            if token_id in self._used_until:
                return False
            self._used_until[token_id] = expires_at
            return True


class RedisReplayStore(ReplayStore):
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)

    def mark_used(self, token_id: str, expires_at: int) -> bool:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        ttl = max(1, expires_at - now_ts)
        return bool(self.client.set(f'plp:replay:{token_id}', 'used', nx=True, ex=ttl))


def build_replay_store(backend: str) -> ReplayStore:
    if backend == 'memory':
        return InMemoryReplayStore()
    if backend == 'redis':
        from app.core.config import settings
        return RedisReplayStore(settings.redis_url)
    raise ValueError(f'Unsupported replay store backend: {backend}')
