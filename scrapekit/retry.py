"""Retry policy with exponential backoff and jitter."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 520, 522, 524})

# Statuses that usually mean "this proxy is blocked or misconfigured",
# not "the target site is down". The client penalises the proxy for these.
PROXY_BLAME_STATUS = frozenset({403, 407, 429})


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: float = 0.3
    retry_status: frozenset = field(default=RETRYABLE_STATUS)

    def should_retry(
        self,
        attempt: int,
        status: Optional[int] = None,
        error: Optional[BaseException] = None,
    ) -> bool:
        if attempt >= self.max_attempts:
            return False
        if error is not None:
            return True
        return status in self.retry_status

    def backoff(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Delay before the next attempt. `attempt` starts at 1."""
        if retry_after is not None:
            return min(retry_after, self.max_delay)
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        spread = delay * self.jitter
        return max(0.0, delay + random.uniform(-spread, spread))


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Parse a Retry-After header given in seconds. The HTTP-date form is ignored."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
