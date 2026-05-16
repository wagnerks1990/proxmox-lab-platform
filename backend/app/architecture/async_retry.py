from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar('T')


@dataclass
class AsyncRetryResult:
    ok: bool
    attempts: int
    value: object | None = None
    error: str | None = None


async def async_retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    jitter: float = 0.1,
    allowed_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> AsyncRetryResult:
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            return AsyncRetryResult(ok=True, attempts=attempt, value=await fn())
        except allowed_exceptions as exc:
            if attempt >= max_attempts:
                return AsyncRetryResult(ok=False, attempts=attempt, error=str(exc))
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, jitter)
            await asyncio.sleep(delay)
    return AsyncRetryResult(ok=False, attempts=attempt, error='retry attempts exhausted')
