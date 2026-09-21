"""Built-in steps."""
from .registry import register
from .serializers import schema_for


class Step:
    """Base class for pipeline steps."""
    name = "step"

    def run(self, data):
        raise NotImplementedError

    def describe(self):
        return {"name": self.name, "schema": schema_for(self)}


@register("upper")
class UpperStep(Step):
    name = "upper"

    def run(self, data):
        return data.upper()


@register("reverse")
class ReverseStep(Step):
    name = "reverse"

    def run(self, data):
        return data[::-1]


@register("prefix")
class PrefixStep(Step):
    name = "prefix"

    def __init__(self, prefix=""):
        self.cfg = {"prefix": prefix}
        self.prefix = prefix

    def run(self, data):
        return self.prefix + data


@register("repeat")
class RepeatStep(Step):
    name = "repeat"

    def __init__(self, times=2):
        self.cfg = {"times": times}
        self.times = times

    def run(self, data):
        return data * self.times
