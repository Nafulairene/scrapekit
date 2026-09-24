import pytest
import requests

from scrapekit import DomainRateLimiter, ProxyPool, RetryPolicy, ScrapeClient


class FakeResponse:
    def __init__(self, status, headers=None):
        self.status_code = status
        self.headers = headers or {}


class FakeSession:
    """Returns queued responses (or raises queued exceptions) in order."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append(kwargs.get("proxies"))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def make_client(outcomes, proxies=None, max_attempts=4):
    sleeps = []
    client = ScrapeClient(
        proxies=proxies,
        limiter=DomainRateLimiter(requests_per_second=1000, sleep=lambda s: None),
        retry=RetryPolicy(max_attempts=max_attempts),
        session=FakeSession(outcomes),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_returns_first_success():
    client, sleeps = make_client([FakeResponse(200)])
    assert client.get("https://x.com").status_code == 200
    assert sleeps == []


def test_retries_503_then_succeeds():
    client, sleeps = make_client([FakeResponse(503), FakeResponse(200)])
    assert client.get("https://x.com").status_code == 200
    assert len(sleeps) == 1


def test_honours_retry_after():
    client, sleeps = make_client([FakeResponse(429, {"Retry-After": "7"}), FakeResponse(200)])
    client.get("https://x.com")
    assert sleeps == [7.0]


def test_gives_up_after_max_attempts():
    client, _ = make_client([FakeResponse(503)] * 3, max_attempts=3)
    assert client.get("https://x.com").status_code == 503


def test_404_is_not_retried():
    client, sleeps = make_client([FakeResponse(404)])
    assert client.get("https://x.com").status_code == 404
    assert sleeps == []


def test_network_error_rotates_proxy():
    pool = ProxyPool(["http://p1", "http://p2"])
    client, _ = make_client([requests.ConnectionError(), FakeResponse(200)], proxies=pool)
    client.get("https://x.com")
    used = [c["https"] for c in client.session.calls]
    assert used == ["http://p1", "http://p2"]
    assert pool._proxies[0].failures == 1


def test_raises_when_errors_exhaust_attempts():
    client, _ = make_client([requests.Timeout()] * 2, max_attempts=2)
    with pytest.raises(requests.Timeout):
        client.get("https://x.com")
