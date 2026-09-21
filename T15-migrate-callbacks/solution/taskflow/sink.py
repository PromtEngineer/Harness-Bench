"""Sink stage: aggregate the final record set into a summary."""
import asyncio


async def collect(records):
    """Aggregate records and return the summary dict."""
    await asyncio.sleep(0)
    by_source = {}
    for r in records:
        by_source[r.source] = by_source.get(r.source, 0) + 1
    return {
        "count": len(records),
        "total": sum(r.value for r in records),
        "by_source": by_source,
    }
