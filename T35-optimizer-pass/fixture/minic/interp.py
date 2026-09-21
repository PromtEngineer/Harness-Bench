"""Stack IR interpreter. DIV/MOD truncate toward zero (C-style)."""


def trunc_div(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero")
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def trunc_mod(a, b):
    return a - trunc_div(a, b) * b


def execute(ir, out=None):
    """Run IR; returns list of printed values (also print()s if out is None)."""
    labels = {arg: i for i, (op, arg) in enumerate(ir) if op == "LABEL"}
    stack = []
    env = {}
    printed = []
    pc = 0
    while pc < len(ir):
        op, arg = ir[pc]
        pc += 1
        if op == "PUSH":
            stack.append(arg)
        elif op == "LOAD":
            stack.append(env[arg])
        elif op == "STORE":
            env[arg] = stack.pop()
        elif op == "POP":
            stack.pop()
        elif op == "NEG":
            stack.append(-stack.pop())
        elif op in ("ADD", "SUB", "MUL", "DIV", "MOD",
                    "LT", "GT", "LE", "GE", "EQ", "NE"):
            b = stack.pop()
            a = stack.pop()
            if op == "ADD":
                stack.append(a + b)
            elif op == "SUB":
                stack.append(a - b)
            elif op == "MUL":
                stack.append(a * b)
            elif op == "DIV":
                stack.append(trunc_div(a, b))
            elif op == "MOD":
                stack.append(trunc_mod(a, b))
            else:
                res = {"LT": a < b, "GT": a > b, "LE": a <= b,
                       "GE": a >= b, "EQ": a == b, "NE": a != b}[op]
                stack.append(1 if res else 0)
        elif op == "PRINT":
            v = stack.pop()
            printed.append(v)
        elif op == "JZ":
            if stack.pop() == 0:
                pc = labels[arg]
        elif op == "JMP":
            pc = labels[arg]
        elif op == "LABEL":
            pass
        else:
            raise ValueError(f"bad op {op}")
    return printed
