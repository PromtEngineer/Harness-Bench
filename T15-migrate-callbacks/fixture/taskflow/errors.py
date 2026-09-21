"""Shared public dataclasses and exception types for taskflow."""
from dataclasses import dataclass


class TaskflowError(Exception):
    """Base class for all taskflow errors."""


class SourceError(TaskflowError):
    """Raised when a source cannot be fetched."""


class TransformError(TaskflowError):
    """Raised when the transform stage rejects its configuration."""


class PipelineError(TaskflowError):
    """Raised by the public API when a pipeline run fails."""


@dataclass(frozen=True)
class Record:
    """One unit of data flowing through the pipeline."""
    source: str
    index: int
    value: int


@dataclass
class PipelineResult:
    """What a completed pipeline run produced."""
    records: list
    errors: list
    summary: dict
