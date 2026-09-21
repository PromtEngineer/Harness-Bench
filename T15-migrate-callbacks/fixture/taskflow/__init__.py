"""taskflow — a small multi-stage data pipeline library."""
from .api import PipelineConfig, run_pipeline
from .errors import PipelineError, PipelineResult, Record

__all__ = ["PipelineConfig", "PipelineError", "PipelineResult", "Record",
           "run_pipeline"]
