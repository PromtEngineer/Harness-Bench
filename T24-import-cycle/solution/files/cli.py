"""flowkit CLI. See docs/CLI.md for the contract."""
import json
import sys

from .pipeline import Pipeline
from .registry import get_registry

USAGE = """usage: python3 -m flowkit.cli <run|list|describe> [args]
  run <pipeline.json> --input <text>
  list
  describe <pipeline.json>"""


def _load_pipeline(path):
    try:
        with open(path) as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError):
        print("error: invalid pipeline file", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(cfg, list):
        print("error: invalid pipeline file", file=sys.stderr)
        raise SystemExit(2)
    try:
        return Pipeline.from_config(cfg)
    except KeyError as exc:
        print(f"error: unknown step '{exc.args[0]}'", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    cmd = argv[0]
    if cmd == "list":
        for name in sorted(get_registry()):
            print(name)
        return
    if cmd == "run":
        if len(argv) != 4 or argv[2] != "--input":
            print(USAGE, file=sys.stderr)
            raise SystemExit(2)
        pipe = _load_pipeline(argv[1])
        print(pipe.run(argv[3]))
        return
    if cmd == "describe":
        if len(argv) != 2:
            print(USAGE, file=sys.stderr)
            raise SystemExit(2)
        print(_load_pipeline(argv[1]).to_json())
        return
    print(USAGE, file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
