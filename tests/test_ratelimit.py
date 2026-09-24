from scrapekit import DomainRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_first_request_is_free_then_waits():
    lim = DomainRateLimiter(requests_per_second=2, clock=FakeClock())
    assert lim.wait_time("https://x.com/1") == 0
    assert lim.wait_time("https://x.com/2") == 0.5


def test_domains_are_independent():
    lim = DomainRateLimiter(requests_per_second=1, clock=FakeClock())
    assert lim.wait_time("https://x.com/") == 0
    assert lim.wait_time("https://y.com/") == 0


def test_tokens_refill_over_time():
    clock = FakeClock()
    lim = DomainRateLimiter(requests_per_second=1, clock=clock)
    lim.wait_time("https://x.com/")
    clock.now = 1.0
    assert lim.wait_time("https://x.com/") == 0


def test_override_per_domain():
    lim = DomainRateLimiter(requests_per_second=1, overrides={"slow.com": 0.5}, clock=FakeClock())
    lim.wait_time("https://slow.com/")
    assert lim.wait_time("https://slow.com/") == 2.0


def test_slow_down_halves_rate_with_floor():
    lim = DomainRateLimiter(requests_per_second=1, min_rate=0.2, clock=FakeClock())
    lim.slow_down("https://x.com/")
    assert lim.current_rate("https://x.com/") == 0.5
    for _ in range(5):
        lim.slow_down("https://x.com/")
    assert lim.current_rate("https://x.com/") == 0.2
