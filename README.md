# 🕷️ scrapekit

Reusable building blocks for scrapers that don't fall over: **proxy rotation**, **per-domain rate limiting**, and **retries with backoff**.

These patterns come from years of helping client developers integrate proxy networks and scraping APIs into their own projects. The same handful of problems came up again and again: one bad proxy poisoning a whole crawl, sites answering with 429s because every request hit at once, and scripts dying on the first timeout. scrapekit packages the fixes.

## Features

* **Proxy pool** with round-robin, random, or success-weighted selection. Failing proxies go on an exponential cooldown instead of being dropped, because most proxy failures are temporary.
* **Per-domain token-bucket rate limiter.** A slow site doesn't throttle the rest of your crawl, and the rate automatically halves after a `429`.
* **Retry policy** with exponential backoff, jitter, and `Retry-After` support. Only retries statuses that are worth retrying (no retrying a `404`).
* **Proxy blame logic.** `403`, `407`, and `429` count against the proxy, not the target site.
* Thread-safe, dependency-light (just `requests`), fully tested.

## Install

```bash
git clone https://github.com/Nafulairene/scrapekit.git
cd scrapekit
pip install -e ".\[dev]"
```

## Quick start

```python
from scrapekit import ProxyPool, DomainRateLimiter, ScrapeClient

pool = ProxyPool.from\_file("proxies.txt", strategy="weighted")
limiter = DomainRateLimiter(requests\_per\_second=2, overrides={"slow-site.com": 0.5})
client = ScrapeClient(proxies=pool, limiter=limiter)

resp = client.get("https://example.com/products")
print(resp.status\_code, len(resp.text))
print(pool.stats())
```

`proxies.txt` holds one proxy URL per line, for example `http://user:pass@host:port`. It's in `.gitignore` so credentials never get committed.

## How the pieces fit

```
request ──► ProxyPool.get() ──► DomainRateLimiter.acquire() ──► HTTP call
                ▲                        ▲                          │
                │ mark\_success/failure   │ slow\_down() on 429       │
                └────────────────────────┴──────── RetryPolicy ◄────┘
```

## Running tests

```bash
pytest -q
```

## Scrape responsibly

Check a site's terms of service and `robots.txt`, keep request rates reasonable, and don't collect personal data you don't have a right to. The default rate limit is deliberately conservative (1 request/second per domain).

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT

