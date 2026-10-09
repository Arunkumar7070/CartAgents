from starlette.requests import Request

from app.rate_limit import TokenBucketLimiter, client_ip


def _request(forwarded_for: str | None, peer: str = "10.0.0.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_forged_forwarded_for_prefix_does_not_change_the_key() -> None:
    honest = _request("203.0.113.7")
    forged = _request("1.2.3.4, 203.0.113.7")
    assert client_ip(honest, trust_proxy=True) == client_ip(forged, trust_proxy=True) == "203.0.113.7"


def test_forwarded_for_is_ignored_without_a_trusted_proxy() -> None:
    assert client_ip(_request("203.0.113.7"), trust_proxy=False) == "10.0.0.1"


def test_bucket_blocks_after_capacity_and_refills_over_time() -> None:
    limiter = TokenBucketLimiter(capacity=2, refill_per_second=1.0)
    assert limiter.allow("ip", now=0.0)
    assert limiter.allow("ip", now=0.0)
    assert not limiter.allow("ip", now=0.0)
    assert limiter.allow("ip", now=1.0)
