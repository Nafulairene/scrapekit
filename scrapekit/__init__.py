"""scrapekit: reusable building blocks for resilient web scrapers."""

from .client import ScrapeClient
from .proxies import NoHealthyProxyError, Proxy, ProxyPool
from .ratelimit import DomainRateLimiter
from .retry import RetryPolicy

__all__ = [
    "Proxy",
    "ProxyPool",
    "NoHealthyProxyError",
    "DomainRateLimiter",
    "RetryPolicy",
    "ScrapeClient",
]
__version__ = "0.1.0"
