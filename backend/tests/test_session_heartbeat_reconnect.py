from app.security.replay_cache import ReplayCache


def test_replay_cache_rejects_duplicate_token_id():
    cache = ReplayCache()
    assert cache.mark_used("jti-1", 9999999999) is True
    assert cache.mark_used("jti-1", 9999999999) is False


def test_replay_cache_evicts_expired_entries():
    cache = ReplayCache()
    assert cache.mark_used("old", 0) is True
    assert cache.mark_used("new", 9999999999) is True
    assert cache.mark_used("old", 9999999999) is True
