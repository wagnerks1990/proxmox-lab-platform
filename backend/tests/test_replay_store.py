from app.security.replay_store import InMemoryReplayStore, build_replay_store


def test_replay_store_duplicate_rejected():
    s = InMemoryReplayStore()
    assert s.mark_used('a', 9999999999)
    assert not s.mark_used('a', 9999999999)


def test_replay_store_expired_evicted():
    s = InMemoryReplayStore()
    assert s.mark_used('a', 0)
    assert s.mark_used('a', 9999999999)


def test_replay_store_import_safety():
    assert build_replay_store('memory') is not None
