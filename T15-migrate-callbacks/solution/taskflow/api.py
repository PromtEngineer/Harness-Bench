"""Public taskflow API: a synchronous entrypoint over the async pipeline."""
import asyncio
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
    return asyncio.run(pipeline.run(config))
