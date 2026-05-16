from threading import Lock


_locks: dict[str, Lock] = {}


def acquire_worker_lock(name: str) -> bool:
    lock = _locks.setdefault(name, Lock())
    return lock.acquire(blocking=False)


def release_worker_lock(name: str) -> None:
    lock = _locks.get(name)
    if lock and lock.locked():
        lock.release()
