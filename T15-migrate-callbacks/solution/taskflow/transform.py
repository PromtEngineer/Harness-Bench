"""Transform stage: scaling then filtering."""
import asyncio
from dataclasses import replace

from .errors import TransformError


async def scale_records(records, multiplier):
    """Multiply every record value; raises TransformError for bad config."""
    if multiplier < 1:
        raise TransformError("multiplier must be >= 1")
    await asyncio.sleep(0)
    return [replace(r, value=r.value * multiplier) for r in records]


async def filter_records(records, drop_below):
    """Keep records whose value is at least drop_below."""
    return [r for r in records if r.value >= drop_below]


async def transform_records(records, config):
    """Scale then filter, returning the ready records."""
    scaled = await scale_records(records, config.multiplier)
    return await filter_records(scaled, config.drop_below)
