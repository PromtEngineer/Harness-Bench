"""Sink stage: aggregate the final record set into a summary."""


def collect(records, on_done):
    """Aggregate records and hand the summary dict to on_done."""
    by_source = {}
    for r in records:
        by_source[r.source] = by_source.get(r.source, 0) + 1
    summary = {
        "count": len(records),
        "total": sum(r.value for r in records),
        "by_source": by_source,
    }
    on_done(summary)
