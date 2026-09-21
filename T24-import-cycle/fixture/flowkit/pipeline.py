"""Pipeline: an ordered list of steps."""
from .registry import build
from .serializers import to_json


class Pipeline:
    def __init__(self, steps):
        self.steps = list(steps)

    @classmethod
    def from_config(cls, cfg):
        """cfg: list of {"step": name, "cfg": {kwargs}} dicts."""
        return cls(build(entry["step"], **entry.get("cfg", {})) for entry in cfg)

    def run(self, data):
        for step in self.steps:
            data = step.run(data)
        return data

    def to_json(self):
        return to_json(self)
