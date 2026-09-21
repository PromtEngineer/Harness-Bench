"""Retry backoff planning."""

BACKOFF_BASE = 2.0
MAX_ATTEMPTS = 5


def backoff_ms(attempt):
    """Delay before the given attempt number (1-based)."""
    if attempt <= 1:
        return 0
    return int(100 * BACKOFF_BASE ** (attempt - 1))


def retry_plan():
    return [backoff_ms(i) for i in range(1, MAX_ATTEMPTS + 1)]
