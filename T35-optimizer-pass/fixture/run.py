#!/usr/bin/env python3
"""CLI: python3 run.py <prog.me> [--opt]  -> executes the program."""
import sys

from minic.interp import execute
sys.path.insert(0, ".")
import compile as compiler

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--opt"]
    for v in execute(compiler.build(args[0], "--opt" in sys.argv)):
        print(v)
