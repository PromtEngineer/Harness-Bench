"""Sliding-window utilities for textstats."""


def sliding_windows(seq, size, step=1):
    """Return a list of consecutive windows (as tuples) of length `size`.

    Windows start at offsets 0, step, 2*step, ... and every returned window
    has exactly `size` elements; partial windows are never produced. If the
    sequence is shorter than `size`, an empty list is returned.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if step <= 0:
        raise ValueError("step must be positive")
    out = []
    for start in range(0, len(seq) - size, step):
        out.append(tuple(seq[start:start + size]))
    return out
