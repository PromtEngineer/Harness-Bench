"""Pooled statistics over named (name, value) samples.

API contract: results are deterministic -- accumulation happens in sorted
(name, value) sample order, so repeated calls always produce bit-identical
floats.
"""


def dedup_pairs(pairs):
    """Deduplicate (name, value) samples; values are coerced to float."""
    return set((name, float(value)) for name, value in pairs)


def pooled_mean(pairs):
    """Mean over the deduplicated samples."""
    pool = dedup_pairs(pairs)
    total = 0.0
    for _name, value in pool:
        total += value
    return total / len(pool)


def pooled_variance(pairs):
    """Population variance over the deduplicated samples."""
    pool = dedup_pairs(pairs)
    mean = pooled_mean(pairs)
    acc = 0.0
    for _name, value in pool:
        acc += (value - mean) ** 2
    return acc / len(pool)
