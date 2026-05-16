from app.workers.lock_store import InMemoryWorkerLockStore, build_lock_store


def test_worker_lock_overlap_prevented():
    s = InMemoryWorkerLockStore()
    assert s.acquire('job', ttl_seconds=60)
    assert not s.acquire('job', ttl_seconds=60)


def test_worker_lock_release_allows_reacquire():
    s = InMemoryWorkerLockStore()
    assert s.acquire('job', ttl_seconds=1)
    s.release('job')
    assert s.acquire('job', ttl_seconds=1)


def test_lock_store_import_safety():
    assert build_lock_store('memory') is not None
