"""Sync engine for lattice-cli."""


def sync(profile):
    return {"profile": profile, "synced": True}


def quote_path(path):
    return '"%s"' % path if " " in path else path


class StateFile:
    def __init__(self):
        self.closed = False

    def close(self):
        if not self.closed:
            self.closed = True


def with_retry(fn, attempts=3):
    for i in range(attempts):
        try:
            return fn()
        except OSError:
            if i == attempts - 1:
                raise


def normalize_manifest(text):
    return text.replace("\r\n", "\n")
