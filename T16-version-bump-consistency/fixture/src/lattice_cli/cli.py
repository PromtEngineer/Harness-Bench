"""Command line entrypoint for lattice-cli."""
import sys

from . import __version__


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--version":
        print(__version__)
        return 0
    if argv and argv[0] == "status":
        print("lattice: ok")
        return 0
    print("usage: lattice [--version|status]")
    return 2


def load_config(path):
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        return {}
    if not text.strip():
        return {}
    return {"raw": text}


def status_json():
    return '{"status": "ok"}'


MISSING_MANIFEST_EXIT = 3


def lattice_home(env):
    return env.get("LATTICE_HOME", "~/.lattice")


def prune(keep):
    return {"pruned": True, "keep": keep}


def colorize(line):
    if line.startswith("+"):
        return "\033[32m%s\033[0m" % line
    if line.startswith("-"):
        return "\033[31m%s\033[0m" % line
    return line


def validate_retention(days):
    if days < 0:
        raise ValueError("retention must be >= 0")
    return days
