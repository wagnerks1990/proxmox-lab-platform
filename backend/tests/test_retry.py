from app.architecture.retry import retry_with_backoff


def test_retry_success():
    counter = {"n": 0}

    def fn():
        counter["n"] += 1
        if counter["n"] < 2:
            raise ValueError("fail once")
        return "ok"

    result = retry_with_backoff(fn, max_attempts=3, base_delay=0)
    assert result.ok
    assert result.value == "ok"


def test_retry_failure():
    def fn():
        raise ValueError("always")

    result = retry_with_backoff(fn, max_attempts=2, base_delay=0)
    assert not result.ok
    assert result.attempts == 2
