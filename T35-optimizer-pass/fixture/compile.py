#!/usr/bin/env python3
"""CLI: python3 compile.py <prog.me> [--opt]  -> prints IR, one op per line."""
import sys

from minic.codegen import generate
from minic.parser import parse


def build(path, opt):
    ir = generate(parse(open(path).read()))
    if opt:
        from minic.optimize import optimize
        ir = optimize(ir)
    return ir


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--opt"]
    ir = build(args[0], "--opt" in sys.argv)
    for op, arg in ir:
        print(op if arg is None else f"{op} {arg}")
