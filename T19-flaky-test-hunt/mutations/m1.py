#!/usr/bin/env python3
"""Mutation m1: re-introduce the unsorted unique_labels bug.

Usage: python3 m1.py <workspace-copy-root>
Reverts statlib/labels.py to the original buggy fixture file. Fails loudly
(nonzero exit) if the solution diverged from the required layout.
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("MUTATION ERROR: usage: m1.py <workspace-root>", file=sys.stderr)
        return 2
    ws = sys.argv[1]
    target = os.path.join(ws, "statlib", "labels.py")
    original = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "originals", "labels.py")
    if not os.path.isfile(target):
        print("MUTATION ERROR: statlib/labels.py not found in the workspace -- "
              "the solution diverged structurally from the required layout",
              file=sys.stderr)
        return 1
    src = open(target).read()
    if "def unique_labels" not in src:
        print("MUTATION ERROR: def unique_labels not found in statlib/labels.py -- "
              "the solution diverged structurally from the required layout",
              file=sys.stderr)
        return 1
    with open(original) as fh:
        buggy = fh.read()
    with open(target, "w") as fh:
        fh.write(buggy)
    print("m1 applied: statlib/labels.py reverted to the original buggy version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
