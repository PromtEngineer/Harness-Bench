"""CLI: python3 -m confl resolve <file>"""
import sys

from . import ConflError, dumps_flat, load


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "resolve":
        print("usage: python3 -m confl resolve <file>", file=sys.stderr)
        raise SystemExit(2)
    try:
        print(dumps_flat(load(sys.argv[2])))
    except ConflError as exc:
        print(f"ConflError: {exc}", file=sys.stderr)
        raise SystemExit(2)


main()
