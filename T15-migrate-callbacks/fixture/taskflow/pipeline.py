"""Pipeline wiring: fan out over sources, transform each batch, then sink."""
from . import sink, source, transform
from .errors import PipelineError, PipelineResult


def run(config, on_complete, on_error):
    """Drive the whole pipeline; ends in on_complete(result) or on_error(exc)."""
    all_records = []
    errors = []
    state = {"failed": False}

    def fail(exc):
        state["failed"] = True
        on_error(exc)

    def process(name):
        def on_fetched(records):
            def on_ready(ready):
                all_records.extend(ready)

            def on_transform_err(exc):
                fail(PipelineError(str(exc)))

            transform.transform_records(records, config, on_ready,
                                        on_transform_err)

        def on_source_err(exc):
            if config.fail_fast:
                fail(PipelineError("%s: %s" % (name, exc)))
            else:
                errors.append("%s: %s" % (name, exc))

        source.fetch(name, on_fetched, on_source_err)

    for name in config.sources:
        process(name)
        if state["failed"]:
            return

    def on_summary(summary):
        on_complete(PipelineResult(records=all_records, errors=errors,
                                   summary=summary))

    sink.collect(all_records, on_summary)
