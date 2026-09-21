# TokenBucketRateLimiter — Specification

Implement a file `ratelimiter.py` at the workspace root containing one public class:

```python
class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float): ...
    def allow(self, key: str, now: float) -> bool: ...
```

Every sentence below is normative.

## Constructor

- `capacity` is the maximum number of tokens a bucket can hold. It must be a
  number strictly greater than 0; otherwise the constructor raises `ValueError`.
- `refill_rate` is the number of tokens added to a bucket per second of elapsed
  time. It must be a number greater than or equal to 0; otherwise the
  constructor raises `ValueError`.
- Non-integer values are allowed for both (e.g. `capacity=0.5`,
  `refill_rate=2.5`).

## Buckets

- Each distinct `key` string has its own fully independent bucket.
- A bucket is created lazily on the first `allow` call for that key. It is
  created FULL (`tokens == capacity`) and its recorded time is set to that
  call's `now`.
- State for one key never affects any other key. In particular, recorded times
  are per key: different keys may be queried with unrelated `now` values in any
  order.

## allow(key, now)

`now` is a caller-supplied monotonic timestamp in seconds (a float). The class
must never read wall-clock time itself.

For a call `allow(key, now)`:

1. **Backwards time check.** If a bucket for `key` already exists and
   `now` is strictly less than the bucket's recorded time, raise `ValueError`.
   The raising call must have NO effect on any state: a later call with a valid
   `now` behaves exactly as if the failing call never happened.
   `now` equal to the recorded time is valid (elapsed time 0).
2. **Refill.** Otherwise, update the bucket:
   `tokens = min(capacity, tokens + (now - recorded_time) * refill_rate)`
   and set the bucket's recorded time to `now`. (For a freshly created bucket
   this is a no-op: it starts full at time `now`.)
3. **Consume.** If `tokens >= 1.0`: subtract exactly `1.0` from `tokens` and
   return `True`.
4. Otherwise return `False`. A denied request consumes nothing, but the
   bucket's recorded time HAS still been updated to `now` in step 2.

Additional requirements:

- The return value must be the built-in `bool` type (`True`/`False`).
- Because an allowed request costs exactly `1.0` token and tokens are capped at
  `capacity`, a limiter with `capacity < 1.0` NEVER allows any request, no
  matter how much time passes.
- Arbitrarily large time jumps are fine: the refill in step 2 is always capped
  at `capacity`.
