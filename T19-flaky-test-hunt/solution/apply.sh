#!/usr/bin/env bash
# Reference solution for T19-flaky-test-hunt. cwd = workspace copy.
# Fixes the three library root causes; tests/ is left untouched.
set -euo pipefail

cat > statlib/labels.py <<'PYEOF'
"""Label handling helpers.

API contract: functions returning collections of labels return them in
deterministic sorted order.
"""


def normalize(label):
    """Lowercase a label and strip surrounding whitespace."""
    return label.strip().lower()


def unique_labels(labels):
    """Return the distinct normalized labels as a sorted list."""
    seen = set()
    for label in labels:
        seen.add(normalize(label))
    return sorted(seen)


def label_histogram(labels):
    """Return {normalized label: occurrences} with keys in sorted order."""
    hist = {}
    for label in labels:
        key = normalize(label)
        hist[key] = hist.get(key, 0) + 1
    return {key: hist[key] for key in sorted(hist)}
PYEOF

cat > statlib/cache.py <<'PYEOF'
"""Scratch-file backed summaries.

cached_summary spills its input to a scratch file and reads it back, which
keeps peak memory flat for very large inputs (the historical reason this
module exists). The scratch file is an implementation detail: callers must
never see it, and concurrent or repeated calls must not interfere.
"""
import os
import tempfile


def parse_line(line):
    """Parse one scratch-file line into a float; None for blank lines."""
    line = line.strip()
    if not line:
        return None
    return float(line)


def cached_summary(values):
    """Spill values to a scratch file, read them back, and summarize.

    Returns {"count": n, "total": sum, "mean": sum / n} (mean 0.0 when empty).
    """
    payload = "\n".join(repr(float(value)) for value in values)
    fd, path = tempfile.mkstemp(prefix="statlib_cache_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(payload)
        total = 0.0
        count = 0
        with open(path) as fh:
            for line in fh:
                value = parse_line(line)
                if value is None:
                    continue
                total += value
                count += 1
    finally:
        os.unlink(path)
    return {"count": count, "total": total, "mean": total / count if count else 0.0}
PYEOF

cat > statlib/stats.py <<'PYEOF'
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
    for _name, value in sorted(pool):
        total += value
    return total / len(pool)


def pooled_variance(pairs):
    """Population variance over the deduplicated samples."""
    pool = dedup_pairs(pairs)
    mean = pooled_mean(pairs)
    acc = 0.0
    for _name, value in sorted(pool):
        acc += (value - mean) ** 2
    return acc / len(pool)
PYEOF

echo "T19 reference solution applied (labels.py, cache.py, stats.py fixed)"
