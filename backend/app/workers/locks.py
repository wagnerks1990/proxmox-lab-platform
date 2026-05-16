from app.core.config import settings
from app.workers.lock_store import build_lock_store

_lock_store = build_lock_store(settings.worker_lock_backend)


def acquire_worker_lock(name: str) -> bool:
    return _lock_store.acquire(name)


def release_worker_lock(name: str) -> None:
    _lock_store.release(name)
