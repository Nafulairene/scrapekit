import pytest

from scrapekit import NoHealthyProxyError, ProxyPool


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_round_robin_cycles_in_order():
    pool = ProxyPool(["a", "b", "c"])
    assert [pool.get().url for _ in range(4)] == ["a", "b", "c", "a"]


def test_failing_proxy_goes_on_cooldown_and_comes_back():
    clock = FakeClock()
    pool = ProxyPool(["a", "b"], max_failures=2, base_cooldown=10, clock=clock)
    a = pool.get()
    pool.mark_failure(a)
    pool.mark_failure(a)
    assert {pool.get().url for _ in range(4)} == {"b"}
    clock.now = 11
    assert "a" in {pool.get().url for _ in range(4)}


def test_all_on_cooldown_raises():
    pool = ProxyPool(["a"], max_failures=1, clock=FakeClock())
    pool.mark_failure(pool.get())
    with pytest.raises(NoHealthyProxyError):
        pool.get()


def test_cooldown_grows_exponentially_and_caps():
    clock = FakeClock()
    pool = ProxyPool(["a"], max_failures=1, base_cooldown=10, max_cooldown=25, clock=clock)
    p = pool._proxies[0]
    pool.mark_failure(p)
    assert p.cooldown_until == 10
    pool.mark_failure(p)
    assert p.cooldown_until == 20
    pool.mark_failure(p)
    assert p.cooldown_until == 25  # capped


def test_success_resets_failure_count():
    pool = ProxyPool(["a"], max_failures=3)
    p = pool.get()
    pool.mark_failure(p)
    pool.mark_success(p)
    assert p.failures == 0 and p.successes == 1


def test_from_file_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "proxies.txt"
    f.write_text("# my proxies\nhttp://a:1\n\nhttp://b:2\n")
    assert len(ProxyPool.from_file(str(f))) == 2


def test_rejects_empty_and_bad_strategy():
    with pytest.raises(ValueError):
        ProxyPool([])
    with pytest.raises(ValueError):
        ProxyPool(["a"], strategy="nope")
