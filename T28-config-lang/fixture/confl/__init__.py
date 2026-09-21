"""CONFL configuration language — IMPLEMENT ME. See SPEC.md."""


class ConflError(Exception):
    pass


def load(path):
    """Parse and fully resolve a CONFL file into a nested dict."""
    raise NotImplementedError("implement confl.load")


def dumps_flat(cfg):
    """Render a nested config dict as sorted 'path=json' lines."""
    raise NotImplementedError("implement confl.dumps_flat")
