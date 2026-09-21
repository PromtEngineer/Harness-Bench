"""Hidden grading suite for TokenBucketRateLimiter (12 cases)."""

import pytest

from ratelimiter import TokenBucketRateLimiter


def test_burst_up_to_capacity_then_denial():
    rl = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is False


def test_fractional_refill_timing():
    rl = TokenBucketRateLimiter(capacity=1, refill_rate=2.0)
    assert rl.allow("k", 0.0) is True      # tokens 0.0
    assert rl.allow("k", 0.25) is False    # 0.5 tokens
    assert rl.allow("k", 0.5) is True      # exactly 1.0 token
    assert rl.allow("k", 0.5) is False


def test_per_key_isolation():
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=0.0)
    assert rl.allow("a", 0.0) is True
    assert rl.allow("a", 0.0) is True
    assert rl.allow("a", 0.0) is False     # a exhausted
    assert rl.allow("b", 0.0) is True      # b unaffected
    assert rl.allow("b", 0.0) is True
    assert rl.allow("b", 0.0) is False


def test_exact_boundary_refill():
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=0.5)
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is True      # tokens 0.0
    assert rl.allow("k", 2.0) is True      # 2.0 s * 0.5/s = exactly 1.0 token
    assert rl.allow("k", 2.0) is False


def test_capacity_below_one_never_allows():
    rl = TokenBucketRateLimiter(capacity=0.5, refill_rate=100.0)
    assert rl.allow("k", 0.0) is False
    assert rl.allow("k", 1.0) is False
    assert rl.allow("k", 1e9) is False


def test_backwards_time_raises_value_error():
    rl = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
    assert rl.allow("k", 100.0) is True
    with pytest.raises(ValueError):
        rl.allow("k", 99.999)


def test_backwards_is_per_key_not_across_keys():
    rl = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
    assert rl.allow("a", 100.0) is True
    assert rl.allow("b", 5.0) is True      # different key, earlier now: fine
    with pytest.raises(ValueError):
        rl.allow("a", 50.0)                # backwards for a
    assert rl.allow("b", 6.0) is True      # b still healthy


def test_large_time_jump_caps_at_capacity():
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=1.0)
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is True      # tokens 0.0
    assert rl.allow("k", 1e6) is True      # refill capped at 2.0
    assert rl.allow("k", 1e6) is True
    assert rl.allow("k", 1e6) is False


def test_constructor_validation():
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=-1.0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=1.0, refill_rate=-0.5)
    TokenBucketRateLimiter(capacity=0.5, refill_rate=0.0)  # valid: no raise


def test_equal_timestamp_is_valid():
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=1.0)
    assert rl.allow("k", 5.0) is True
    assert rl.allow("k", 5.0) is True      # now == recorded time: elapsed 0
    assert rl.allow("k", 5.0) is False     # not an error, just denied


def test_denied_request_consumes_nothing():
    rl = TokenBucketRateLimiter(capacity=2, refill_rate=2.0)
    assert rl.allow("k", 0.0) is True
    assert rl.allow("k", 0.0) is True      # tokens 0.0
    assert rl.allow("k", 0.0) is False     # denied, still 0.0 tokens
    assert rl.allow("k", 0.5) is True      # +1.0 token refilled
    assert rl.allow("k", 0.5) is False


def test_error_has_no_state_effect_and_returns_bool():
    rl = TokenBucketRateLimiter(capacity=1, refill_rate=1.0)
    r = rl.allow("k", 10.0)
    assert isinstance(r, bool) and r is True   # tokens 0.0, time 10.0
    with pytest.raises(ValueError):
        rl.allow("k", 5.0)
    r2 = rl.allow("k", 10.5)                   # 0.5 tokens: denied
    assert isinstance(r2, bool) and r2 is False
    assert rl.allow("k", 11.0) is True         # exactly 1.0 token
