from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock


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


def build_replay_store(backend: str) -> ReplayStore:
    if backend == 'memory':
        return InMemoryReplayStore()
    if backend in {'redis', 'database'}:
        return InMemoryReplayStore()
    raise ValueError(f'Unsupported replay store backend: {backend}')
