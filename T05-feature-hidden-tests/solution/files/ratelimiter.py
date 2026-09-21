"""Reference implementation of TokenBucketRateLimiter (see spec.md)."""


class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float):
        if not capacity > 0:
            raise ValueError("capacity must be > 0")
        if not refill_rate >= 0:
            raise ValueError("refill_rate must be >= 0")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._buckets = {}  # key -> (tokens, recorded_time)

    def allow(self, key: str, now: float) -> bool:
        bucket = self._buckets.get(key)
        if bucket is None:
            tokens = self.capacity
        else:
            tokens, recorded = bucket
            if now < recorded:
                raise ValueError(
                    "time went backwards for key %r: %r < %r" % (key, now, recorded)
                )
            tokens = min(self.capacity, tokens + (now - recorded) * self.refill_rate)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._buckets[key] = (tokens, now)
        return allowed
