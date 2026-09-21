"""JSON serialization helpers (added for the audit-export feature)."""
import json

from .pipeline import Pipeline
from .steps import Step


def to_json(pipeline):
    if not isinstance(pipeline, Pipeline):
        raise TypeError("to_json expects a Pipeline")
    return json.dumps({"steps": [s.describe() for s in pipeline.steps]},
                      sort_keys=True)


def schema_for(step):
    if not isinstance(step, Step):
        raise TypeError("schema_for expects a Step")
    cfg = getattr(step, "cfg", {})
    return {"type": step.name, "options": sorted(cfg)}
