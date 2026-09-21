"""flowkit: tiny text-processing pipeline framework."""
from .pipeline import Pipeline
from .registry import build, get_registry, register
from .steps import Step

__all__ = ["Pipeline", "Step", "build", "get_registry", "register"]
