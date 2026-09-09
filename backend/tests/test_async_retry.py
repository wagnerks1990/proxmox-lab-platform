import pytest
from app.architecture.async_retry import async_retry_with_backoff


@pytest.mark.asyncio
async def test_async_retry_success():
    state = {"n": 0}

    async def fn():
        state["n"] += 1
        if state["n"] < 2:
            raise ValueError("fail once")
        return "ok"

    rr = await async_retry_with_backoff(fn, max_attempts=3, base_delay=0)
    assert rr.ok
    assert rr.value == "ok"


@pytest.mark.asyncio
async def test_async_retry_failure():
    async def fn():
        raise ValueError("always")

    rr = await async_retry_with_backoff(fn, max_attempts=2, base_delay=0)
    assert not rr.ok
    assert rr.attempts == 2
