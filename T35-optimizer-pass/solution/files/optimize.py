"""Reference IR optimizer for T35 (constant folding, identities,
constant branches, unreachable code, dead stores)."""
from .interp import trunc_div, trunc_mod

_FOLD = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "MUL": lambda a, b: a * b,
    "LT": lambda a, b: 1 if a < b else 0,
    "GT": lambda a, b: 1 if a > b else 0,
    "LE": lambda a, b: 1 if a <= b else 0,
    "GE": lambda a, b: 1 if a >= b else 0,
    "EQ": lambda a, b: 1 if a == b else 0,
    "NE": lambda a, b: 1 if a != b else 0,
}


def _peephole(ir):
    out = []
    changed = False
    i = 0
    while i < len(ir):
        op, arg = ir[i]
        # PUSH a, PUSH b, binop -> PUSH folded
        if (op == "PUSH" and i + 2 < len(ir) and ir[i + 1][0] == "PUSH"):
            op2 = ir[i + 2][0]
            a, b = arg, ir[i + 1][1]
            if op2 in _FOLD:
                out.append(("PUSH", _FOLD[op2](a, b)))
                i += 3
                changed = True
                continue
            if op2 in ("DIV", "MOD") and b != 0:
                fn = trunc_div if op2 == "DIV" else trunc_mod
                out.append(("PUSH", fn(a, b)))
                i += 3
                changed = True
                continue
        # PUSH a, NEG -> PUSH -a
        if op == "PUSH" and i + 1 < len(ir) and ir[i + 1][0] == "NEG":
            out.append(("PUSH", -arg))
            i += 2
            changed = True
            continue
        # identities: PUSH 0 ADD / PUSH 0 SUB / PUSH 1 MUL / PUSH 1 DIV
        if op == "PUSH" and i + 1 < len(ir):
            nxt = ir[i + 1][0]
            if (arg == 0 and nxt in ("ADD", "SUB")) or \
               (arg == 1 and nxt in ("MUL", "DIV")):
                i += 2
                changed = True
                continue
        # constant branch: PUSH c, JZ L
        if op == "PUSH" and i + 1 < len(ir) and ir[i + 1][0] == "JZ":
            if arg == 0:
                out.append(("JMP", ir[i + 1][1]))
            i += 2
            changed = True
            continue
        # PUSH c, POP -> nothing
        if op == "PUSH" and i + 1 < len(ir) and ir[i + 1][0] == "POP":
            i += 2
            changed = True
            continue
        out.append((op, arg))
        i += 1
    return out, changed


def _unreachable(ir):
    out = []
    changed = False
    skipping = False
    for op, arg in ir:
        if skipping:
            if op == "LABEL":
                skipping = False
                out.append((op, arg))
            else:
                changed = True
            continue
        out.append((op, arg))
        if op == "JMP":
            skipping = True
    return out, changed


def _dead_stores(ir):
    loaded = {arg for op, arg in ir if op == "LOAD"}
    out = []
    changed = False
    for op, arg in ir:
        if op == "STORE" and arg not in loaded:
            out.append(("POP", None))
            changed = True
        else:
            out.append((op, arg))
    return out, changed


def optimize(ir):
    ir = list(ir)
    while True:
        changed = False
        for fn in (_peephole, _unreachable, _dead_stores):
            ir, ch = fn(ir)
            changed = changed or ch
        if not changed:
            return ir
