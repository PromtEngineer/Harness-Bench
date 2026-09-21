#!/usr/bin/env python3
"""Mutation m2: re-introduce the fixed-tmpfile-path / no-cleanup bug.

Usage: python3 m2.py <workspace-copy-root>
Reverts statlib/cache.py to the original buggy fixture file. Fails loudly
(nonzero exit) if the solution diverged from the required layout.
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("MUTATION ERROR: usage: m2.py <workspace-root>", file=sys.stderr)
        return 2
    ws = sys.argv[1]
    target = os.path.join(ws, "statlib", "cache.py")
    original = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "originals", "cache.py")
    if not os.path.isfile(target):
        print("MUTATION ERROR: statlib/cache.py not found in the workspace -- "
              "the solution diverged structurally from the required layout",
              file=sys.stderr)
        return 1
    src = open(target).read()
    if "def cached_summary" not in src:
        print("MUTATION ERROR: def cached_summary not found in statlib/cache.py -- "
              "the solution diverged structurally from the required layout",
              file=sys.stderr)
        return 1
    with open(original) as fh:
        buggy = fh.read()
    with open(target, "w") as fh:
        fh.write(buggy)
    print("m2 applied: statlib/cache.py reverted to the original buggy version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
