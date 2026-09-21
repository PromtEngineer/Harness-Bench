"""Pipeline wiring: fan out over sources concurrently, then sink."""
import asyncio

from . import sink, source, transform
from .errors import PipelineError, PipelineResult, SourceError, TransformError


async def _process_source(name, config):
    """Fetch and transform one source, tagging the outcome."""
    try:
        records = await source.fetch(name)
    except SourceError as exc:
        return ("error", "%s: %s" % (name, exc))
    ready = await transform.transform_records(records, config)
    return ("ok", ready)


async def run(config):
    """Run the whole pipeline for `config` and return a PipelineResult."""
    try:
        outcomes = await asyncio.gather(
            *(_process_source(name, config) for name in config.sources))
    except TransformError as exc:
        raise PipelineError(str(exc)) from exc

    all_records = []
    errors = []
    for kind, payload in outcomes:
        if kind == "error":
            if config.fail_fast:
                raise PipelineError(payload)
            errors.append(payload)
        else:
            all_records.extend(payload)
    summary = await sink.collect(all_records)
    return PipelineResult(records=all_records, errors=errors, summary=summary)
