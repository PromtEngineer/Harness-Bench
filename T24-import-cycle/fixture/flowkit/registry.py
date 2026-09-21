"""Step registry."""

_REG = {}


def register(name):
    """Class decorator: register a Step subclass under a name."""
    def deco(cls):
        _REG[name] = cls
        return cls
    return deco


def get_registry():
    """Return a copy of the registry mapping name -> class."""
    return dict(_REG)


def build(name, **cfg):
    """Instantiate a registered step by name."""
    if name not in _REG:
        raise KeyError(name)
    return _REG[name](**cfg)
