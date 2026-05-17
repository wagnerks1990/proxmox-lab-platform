from app.workers.locks import acquire_worker_lock, release_worker_lock


def test_worker_lock_prevents_overlap():
    assert acquire_worker_lock('x')
    assert not acquire_worker_lock('x')
    release_worker_lock('x')
