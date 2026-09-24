"""A requests-based client that ties proxies, rate limiting and retries together."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import requests

from .proxies import ProxyPool
from .ratelimit import DomainRateLimiter
from .retry import PROXY_BLAME_STATUS, RetryPolicy, parse_retry_after

log = logging.getLogger("scrapekit")

DEFAULT_HEADERS = {
    "User-Agent": "scrapekit/0.1 (+https://github.com/Nafulairene/scrapekit)",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}


class ScrapeClient:
    """Fetch URLs through a proxy pool, respecting per-domain rate limits.

    Example:
        pool = ProxyPool(["http://user:pass@p1:8000", "http://user:pass@p2:8000"])
        client = ScrapeClient(proxies=pool, limiter=DomainRateLimiter(2.0))
        html = client.get("https://example.com").text
    """

    def __init__(
        self,
        proxies: Optional[ProxyPool] = None,
        limiter: Optional[DomainRateLimiter] = None,
        retry: Optional[RetryPolicy] = None,
        timeout: float = 20.0,
        headers: Optional[dict] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.proxies = proxies
        self.limiter = limiter or DomainRateLimiter()
        self.retry = retry or RetryPolicy()
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)
        self._sleep = sleep

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        attempt = 0
        while True:
            attempt += 1
            proxy = self.proxies.get() if self.proxies else None
            if proxy:
                kwargs["proxies"] = {"http": proxy.url, "https": proxy.url}
            self.limiter.acquire(url)

            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                if proxy:
                    self.proxies.mark_failure(proxy)
                if not self.retry.should_retry(attempt, error=exc):
                    raise
                delay = self.retry.backoff(attempt)
                log.warning(
                    "%s %s failed (%s); retry %d in %.1fs",
                    method, url, exc.__class__.__name__, attempt, delay,
                )
                self._sleep(delay)
                continue

            if proxy:
                if resp.status_code in PROXY_BLAME_STATUS:
                    self.proxies.mark_failure(proxy)
                else:
                    self.proxies.mark_success(proxy)
            if resp.status_code == 429:
                self.limiter.slow_down(url)

            if not self.retry.should_retry(attempt, status=resp.status_code):
                return resp

            delay = self.retry.backoff(
                attempt, parse_retry_after(resp.headers.get("Retry-After"))
            )
            log.warning(
                "%s %s -> %d; retry %d in %.1fs",
                method, url, resp.status_code, attempt, delay,
            )
            self._sleep(delay)
