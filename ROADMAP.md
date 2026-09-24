# Roadmap

- [x] v0.1: core library (proxy pool, rate limiter, retry policy, client), tests, CI
- [ ] `robots.txt` checker that the client can consult before fetching
- [ ] User-agent rotation helper
- [ ] Async client (`httpx` / `aiohttp`) sharing the same proxy pool and limiter
- [ ] **Scrapy template**: downloader middleware wrapping `ProxyPool` + example spider
- [ ] **Selenium template**: headless Chrome with proxy auth and explicit waits
- [ ] **Puppeteer template** (Node): rotating proxies, request interception, retries
- [ ] Proxy health-check CLI (`python -m scrapekit.check proxies.txt`)
- [ ] Output pipelines: JSONL / CSV writers with deduplication
- [ ] Docs page with architecture notes and common failure modes
