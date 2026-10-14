import time
from dataclasses import dataclass, field

from fastapi import Request


def client_ip(request: Request, trust_proxy: bool) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if trust_proxy and forwarded_for:
        # The proxy appends the address it saw, so only the right-most entry is not client-controlled.
        return forwarded_for.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@dataclass
class TokenBucketLimiter:
    capacity: int
    refill_per_second: float
    _buckets: dict[str, tuple[float, float]] = field(default_factory=dict)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        tokens, last = self._buckets.get(key, (float(self.capacity), now))
        tokens = min(self.capacity, tokens + (now - last) * self.refill_per_second)
        if tokens < 1:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - 1, now)
        return True
