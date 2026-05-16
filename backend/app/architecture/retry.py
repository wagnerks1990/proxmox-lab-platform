from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar('T')


@dataclass
class RetryResult:
    ok: bool
    attempts: int
    value: object | None = None
    error: str | None = None


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    jitter: float = 0.1,
    allowed_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> RetryResult:
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            return RetryResult(ok=True, attempts=attempt, value=fn())
        except allowed_exceptions as exc:
            if attempt >= max_attempts:
                return RetryResult(ok=False, attempts=attempt, error=str(exc))
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, jitter)
            time.sleep(delay)
    return RetryResult(ok=False, attempts=attempt, error='retry attempts exhausted')
