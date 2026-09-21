"""Small numeric utilities."""


def mean(values):
    """Arithmetic mean of a non-empty sequence."""
    values = list(values)
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def median(values):
    """Median of a non-empty sequence."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median of empty sequence")
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def clamp(value, low, high):
    """Clamp value into the inclusive range [low, high]."""
    if low > high:
        raise ValueError("low > high")
    return max(low, min(high, value))


def rolling_sum(values, window):
    """Sliding-window sums; len(result) == max(0, len(values) - window + 1)."""
    if window <= 0:
        raise ValueError("window must be positive")
    out = []
    acc = 0.0
    for i, value in enumerate(values):
        acc += value
        if i >= window:
            acc -= values[i - window]
        if i >= window - 1:
            out.append(acc)
    return out
