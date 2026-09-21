"""Public taskflow API: a synchronous entrypoint over the pipeline."""
from dataclasses import dataclass

from . import pipeline
from .errors import PipelineError, PipelineResult, Record  # noqa: F401


@dataclass
class PipelineConfig:
    """Configuration for one pipeline run."""
    sources: list
    multiplier: int = 1
    drop_below: int = 0
    fail_fast: bool = False


def run_pipeline(config):
    """Run the pipeline synchronously and return a PipelineResult."""
    holder = {}

    def on_complete(result):
        holder["result"] = result

    def on_error(exc):
        holder["error"] = exc

    pipeline.run(config, on_complete, on_error)
    if "error" in holder:
        raise holder["error"]
    return holder["result"]
