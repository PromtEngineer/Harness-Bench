"""Data sources. fetch() delivers records via callbacks."""
from zlib import crc32

from .errors import Record, SourceError


def _raw_values(name):
    """Deterministic values for a source name.

    h = crc32(utf8(name)); count = h % 5 + 3; value_i = (h + i * 37) % 100
    """
    h = crc32(name.encode("utf-8"))
    return [(h + i * 37) % 100 for i in range(h % 5 + 3)]


def fetch(name, on_ok, on_err):
    """Fetch records for `name`; invokes on_ok(records) or on_err(exc)."""
    if name.startswith("bad"):
        on_err(SourceError("source %s unavailable" % name))
        return
    records = [Record(source=name, index=i, value=v)
               for i, v in enumerate(_raw_values(name))]
    on_ok(records)
