"""JSON serialization helpers (added for the audit-export feature).

Imports of Pipeline/Step are deferred into the functions to break the
import cycles serializers<->pipeline and serializers<->steps.
"""
import json


def to_json(pipeline):
    from .pipeline import Pipeline
    if not isinstance(pipeline, Pipeline):
        raise TypeError("to_json expects a Pipeline")
    return json.dumps({"steps": [s.describe() for s in pipeline.steps]},
                      sort_keys=True)


def schema_for(step):
    from .steps import Step
    if not isinstance(step, Step):
        raise TypeError("schema_for expects a Step")
    cfg = getattr(step, "cfg", {})
    return {"type": step.name, "options": sorted(cfg)}
