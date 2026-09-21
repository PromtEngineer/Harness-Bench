"""Runnable usage examples for TokenBucketRateLimiter.

Run with:  python3 examples.py
All four examples must complete without AssertionError once ratelimiter.py
is implemented per spec.md.
"""

from ratelimiter import TokenBucketRateLimiter


def example_1_burst_then_denial():
    """A bucket starts full: capacity requests pass, then denial."""
    rl = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
    results = [rl.allow("api", 0.0) for _ in range(4)]
    assert results == [True, True, True, False], results
    print("example 1 ok:", results)


def example_2_continuous_refill():
    """Tokens refill continuously; a request needs a full 1.0 token."""
    rl = TokenBucketRateLimiter(capacity=1, refill_rate=2.0)
    assert rl.allow("user", 0.0) is True     # bucket drained to 0.0
    assert rl.allow("user", 0.25) is False   # only 0.5 tokens so far
    assert rl.allow("user", 0.5) is True     # exactly 1.0 token -> allowed
    print("example 2 ok")


def example_3_per_key_buckets():
    """Keys are independent, including their notion of time."""
    rl = TokenBucketRateLimiter(capacity=1, refill_rate=1.0)
    assert rl.allow("alice", 100.0) is True
    assert rl.allow("bob", 50.0) is True     # earlier 'now' but different key: fine
    assert rl.allow("alice", 100.0) is False
    print("example 3 ok")


def example_4_backwards_time():
    """Per-key backwards time raises ValueError and changes nothing."""
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=1.0)
    assert rl.allow("k", 10.0) is True       # tokens now 1.0
    try:
        rl.allow("k", 9.0)
        raise AssertionError("expected ValueError for backwards time")
    except ValueError:
        pass
    assert rl.allow("k", 10.0) is True       # failed call had no effect
    print("example 4 ok")


if __name__ == "__main__":
    example_1_burst_then_denial()
    example_2_continuous_refill()
    example_3_per_key_buckets()
    example_4_backwards_time()
    print("all examples passed")
