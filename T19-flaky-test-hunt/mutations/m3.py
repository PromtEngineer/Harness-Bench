#!/usr/bin/env python3
"""Mutation m3: re-introduce the set-order float accumulation bug.

Usage: python3 m3.py <workspace-copy-root>
Reverts statlib/stats.py to the original buggy fixture file. Fails loudly
(nonzero exit) if the solution diverged from the required layout.
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("MUTATION ERROR: usage: m3.py <workspace-root>", file=sys.stderr)
        return 2
    ws = sys.argv[1]
    target = os.path.join(ws, "statlib", "stats.py")
    original = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "originals", "stats.py")
    if not os.path.isfile(target):
        print("MUTATION ERROR: statlib/stats.py not found in the workspace -- "
              "the solution diverged structurally from the required layout",
              file=sys.stderr)
        return 1
    src = open(target).read()
    if "def pooled_variance" not in src or "def pooled_mean" not in src:
        print("MUTATION ERROR: pooled_mean/pooled_variance not found in "
              "statlib/stats.py -- the solution diverged structurally from the "
              "required layout", file=sys.stderr)
        return 1
    with open(original) as fh:
        buggy = fh.read()
    with open(target, "w") as fh:
        fh.write(buggy)
    print("m3 applied: statlib/stats.py reverted to the original buggy version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
