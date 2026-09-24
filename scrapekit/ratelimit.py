"""Per-domain rate limiting using a token bucket.

Each domain gets its own bucket, so a slow target site does not throttle
requests to every other site in the same crawl.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlparse


@dataclass
class _Bucket:
    capacity: float
    rate: float  # tokens per second
    tokens: float
    updated: float

    def refill(self, now: float) -> None:
        elapsed = now - self.updated
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated = now


@dataclass
class DomainRateLimiter:
    requests_per_second: float = 1.0
    burst: int = 1
    overrides: dict = field(default_factory=dict)
    min_rate: float = 0.05
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    _buckets: dict = field(init=False, default_factory=dict)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    @staticmethod
    def domain_of(url: str) -> str:
        return urlparse(url).netloc.lower()

    def _bucket_for(self, domain: str) -> _Bucket:
        if domain not in self._buckets:
            rate = self.overrides.get(domain, self.requests_per_second)
            self._buckets[domain] = _Bucket(
                capacity=float(self.burst),
                rate=rate,
                tokens=float(self.burst),
                updated=self.clock(),
            )
        return self._buckets[domain]

    def wait_time(self, url: str) -> float:
        """Reserve a slot for this URL and return how long to wait for it."""
        with self._lock:
            bucket = self._bucket_for(self.domain_of(url))
            bucket.refill(self.clock())
            bucket.tokens -= 1
            if bucket.tokens >= 0:
                return 0.0
            return -bucket.tokens / bucket.rate

    def acquire(self, url: str) -> float:
        """Block until a request to this URL's domain is allowed."""
        delay = self.wait_time(url)
        if delay > 0:
            self.sleep(delay)
        return delay

    def slow_down(self, url: str, factor: float = 0.5) -> None:
        """Reduce a domain's rate, e.g. after a 429 response."""
        with self._lock:
            bucket = self._bucket_for(self.domain_of(url))
            bucket.rate = max(bucket.rate * factor, self.min_rate)

    def current_rate(self, url: str) -> float:
        with self._lock:
            return self._bucket_for(self.domain_of(url)).rate
