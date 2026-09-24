"""Proxy rotation with health tracking.

Proxies that fail repeatedly are put on a cooldown instead of being dropped,
because most proxy failures are temporary (bans, timeouts, overloaded exits).
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable


class NoHealthyProxyError(RuntimeError):
    """Raised when every proxy in the pool is cooling down."""


@dataclass
class Proxy:
    url: str
    failures: int = 0
    successes: int = 0
    cooldown_until: float = 0.0

    def is_available(self, now: float) -> bool:
        return now >= self.cooldown_until

    @property
    def success_rate(self) -> float:
        total = self.failures + self.successes
        return 1.0 if total == 0 else self.successes / total


@dataclass
class ProxyPool:
    """Thread-safe pool of proxies.

    strategy:
        "round_robin" - cycle through available proxies in order
        "random"      - pick any available proxy
        "weighted"    - favour proxies with a better success rate
    """

    urls: Iterable[str]
    strategy: str = "round_robin"
    max_failures: int = 3
    base_cooldown: float = 30.0
    max_cooldown: float = 600.0
    clock: Callable[[], float] = time.monotonic
    _proxies: list = field(init=False)
    _index: int = field(init=False, default=0)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self._proxies = [Proxy(u) for u in self.urls]
        if not self._proxies:
            raise ValueError("ProxyPool needs at least one proxy URL")
        if self.strategy not in {"round_robin", "random", "weighted"}:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    @classmethod
    def from_file(cls, path: str, **kwargs) -> "ProxyPool":
        """Load one proxy URL per line; blank lines and # comments are skipped."""
        with open(path, encoding="utf-8") as fh:
            urls = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        return cls(urls, **kwargs)

    def __len__(self) -> int:
        return len(self._proxies)

    def get(self) -> Proxy:
        with self._lock:
            now = self.clock()
            available = [p for p in self._proxies if p.is_available(now)]
            if not available:
                soonest = min(p.cooldown_until for p in self._proxies) - now
                raise NoHealthyProxyError(
                    f"All proxies cooling down; next free in {soonest:.1f}s"
                )
            if self.strategy == "random":
                return random.choice(available)
            if self.strategy == "weighted":
                weights = [max(p.success_rate, 0.05) for p in available]
                return random.choices(available, weights=weights, k=1)[0]
            # round robin over the full list, skipping proxies on cooldown
            while True:
                proxy = self._proxies[self._index % len(self._proxies)]
                self._index += 1
                if proxy.is_available(now):
                    return proxy

    def mark_success(self, proxy: Proxy) -> None:
        with self._lock:
            proxy.successes += 1
            proxy.failures = 0

    def mark_failure(self, proxy: Proxy) -> None:
        with self._lock:
            proxy.failures += 1
            if proxy.failures >= self.max_failures:
                # exponential cooldown: 30s, 60s, 120s ... capped at max_cooldown
                extra = proxy.failures - self.max_failures
                delay = min(self.base_cooldown * (2 ** extra), self.max_cooldown)
                proxy.cooldown_until = self.clock() + delay

    def stats(self) -> list:
        now = self.clock()
        return [
            {
                "url": p.url,
                "successes": p.successes,
                "failures": p.failures,
                "available": p.is_available(now),
            }
            for p in self._proxies
        ]
