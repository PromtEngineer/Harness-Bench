"""Scratch-file backed summaries.

cached_summary spills its input to a scratch file and reads it back, which
keeps peak memory flat for very large inputs (the historical reason this
module exists). The scratch file is an implementation detail: callers must
never see it, and concurrent or repeated calls must not interfere.
"""

CACHE_PATH = "/tmp/statlib_cache.tmp"


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
    fh = open(CACHE_PATH, "x")
    fh.write(payload)
    fh.close()
    total = 0.0
    count = 0
    with open(CACHE_PATH) as fh:
        for line in fh:
            value = parse_line(line)
            if value is None:
                continue
            total += value
            count += 1
    return {"count": count, "total": total, "mean": total / count if count else 0.0}
