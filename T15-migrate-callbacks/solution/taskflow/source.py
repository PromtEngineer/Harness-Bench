"""Data sources. fetch() returns records asynchronously."""
import asyncio
from zlib import crc32

from .errors import Record, SourceError


def _raw_values(name):
    """Deterministic values for a source name.

    h = crc32(utf8(name)); count = h % 5 + 3; value_i = (h + i * 37) % 100
    """
    h = crc32(name.encode("utf-8"))
    return [(h + i * 37) % 100 for i in range(h % 5 + 3)]


async def fetch(name):
    """Fetch records for `name`; raises SourceError when unavailable."""
    await asyncio.sleep(0)
    if name.startswith("bad"):
        raise SourceError("source %s unavailable" % name)
    return [Record(source=name, index=i, value=v)
            for i, v in enumerate(_raw_values(name))]
