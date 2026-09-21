"""Transform stage: scaling then filtering, chained through callbacks."""
from dataclasses import replace

from .errors import TransformError


def scale_records(records, multiplier, on_ok, on_err):
    """Multiply every record value; on_err(TransformError) for bad config."""
    if multiplier < 1:
        on_err(TransformError("multiplier must be >= 1"))
        return
    on_ok([replace(r, value=r.value * multiplier) for r in records])


def filter_records(records, drop_below, on_ok, on_err):
    """Keep records whose value is at least drop_below."""
    on_ok([r for r in records if r.value >= drop_below])


def transform_records(records, config, on_ok, on_err):
    """Scale then filter, invoking on_ok(ready) or on_err(exc)."""

    def after_scale(scaled):
        filter_records(scaled, config.drop_below, on_ok, on_err)

    scale_records(records, config.multiplier, after_scale, on_err)
