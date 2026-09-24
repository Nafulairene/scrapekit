"""Fetch a few pages through a rotating proxy pool.

Usage:
    python examples/basic_fetch.py proxies.txt
Without a proxies file, requests go out directly.
"""

import logging
import sys

from scrapekit import DomainRateLimiter, ProxyPool, ScrapeClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

URLS = [
    "https://httpbin.org/ip",
    "https://httpbin.org/status/503",
    "https://httpbin.org/headers",
]

pool = ProxyPool.from_file(sys.argv[1]) if len(sys.argv) > 1 else None
client = ScrapeClient(proxies=pool, limiter=DomainRateLimiter(requests_per_second=1))

for url in URLS:
    resp = client.get(url)
    print(url, "->", resp.status_code)

if pool:
    for row in pool.stats():
        print(row)
