#!/usr/bin/env python3
"""Spreadsheet evaluator per SPEC.md. Usage: calc.py <sheet.tsv> <out.tsv>"""
import sys

sys.setrecursionlimit(1_000_000)

ERR_RANK = {"#CYCLE!": 3, "#REF!": 2, "#DIV/0!": 1}


def is_err(v):
    return isinstance(v, str)


def worst(errs):
    return max(errs, key=lambda e: ERR_RANK[e])


def col_to_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def parse_ref(tok):
    i = 0
    while i < len(tok) and tok[i].isalpha():
        i += 1
    return (int(tok[i:]), col_to_num(tok[:i]))  # (row, col)


def tokenize(f):
    toks = []
    i = 0
    while i < len(f):
        c = f[i]
        if c == " ":
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < len(f) and f[j].isdigit():
                j += 1
            toks.append(("int", int(f[i:j])))
            i = j
        elif c.isalpha():
            j = i
            while j < len(f) and f[j].isalpha():
                j += 1
            k = j
            while k < len(f) and f[k].isdigit():
                k += 1
            word = f[i:k].upper()
            if k > j:
                toks.append(("cell", word))
            else:
                toks.append(("name", word))
            i = k
        elif c == "<":
            if f[i:i + 2] == "<=":
                toks.append(("op", "<="))
                i += 2
            elif f[i:i + 2] == "<>":
                toks.append(("op", "<>"))
                i += 2
            else:
                toks.append(("op", "<"))
                i += 1
        elif c == ">":
            if f[i:i + 2] == ">=":
                toks.append(("op", ">="))
                i += 2
            else:
                toks.append(("op", ">"))
                i += 1
        elif c in "+-*/%(),:=":
            toks.append(("op", c))
            i += 1
        else:
            raise ValueError(f"bad char {c!r} in formula {f!r}")
    toks.append(("end", ""))
    return toks


class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self):
        return self.t[self.i]

    def take(self, val=None):
        k, v = self.t[self.i]
        self.i += 1
        if val is not None and v != val:
            raise ValueError(f"expected {val!r}, got {v!r}")
        return v

    def parse(self):
        node = self.comparison()
        if self.peek()[0] != "end":
            raise ValueError(f"trailing tokens: {self.t[self.i:]}")
        return node

    def comparison(self):
        left = self.additive()
        while self.peek() == ("op", "=") or self.peek()[1] in (
                "<", ">", "<=", ">=", "<>"):
            op = self.take()
            left = ("cmp", op, left, self.additive())
        return left

    def additive(self):
        left = self.term()
        while self.peek()[1] in ("+", "-"):
            op = self.take()
            left = ("bin", op, left, self.term())
        return left

    def term(self):
        left = self.unary()
        while self.peek()[1] in ("*", "/", "%"):
            op = self.take()
            left = ("bin", op, left, self.unary())
        return left

    def unary(self):
        if self.peek()[1] == "-":
            self.take()
            return ("neg", self.unary())
        return self.atom()

    def atom(self):
        kind, val = self.peek()
        if kind == "int":
            self.take()
            return ("int", val)
        if kind == "cell":
            self.take()
            return ("ref", val)
        if kind == "name":
            self.take()
            self.take("(")
            if val == "IF":
                a = self.comparison()
                self.take(",")
                b = self.comparison()
                self.take(",")
                c = self.comparison()
                self.take(")")
                return ("if", a, b, c)
            lo = self.take()
            self.take(":")
            hi = self.take()
            self.take(")")
            return ("range_fn", val, lo, hi)
        if val == "(":
            self.take()
            node = self.comparison()
            self.take(")")
            return node
        raise ValueError(f"unexpected token {val!r}")


def trunc_div(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


class Sheet:
    def __init__(self, cells):
        self.cells = cells          # (row, col) -> raw content str
        self.memo = {}
        self.gray = set()
        self.ast = {}

    def cell_value(self, rc):
        if rc in self.memo:
            return self.memo[rc]
        if rc not in self.cells:
            return "#REF!"
        if rc in self.gray:
            return "#CYCLE!"
        self.gray.add(rc)
        try:
            raw = self.cells[rc]
            if raw.startswith("="):
                if rc not in self.ast:
                    self.ast[rc] = Parser(tokenize(raw[1:])).parse()
                v = self.eval(self.ast[rc])
            else:
                v = int(raw)
        finally:
            self.gray.discard(rc)
        self.memo[rc] = v
        return v

    def eval(self, node):
        kind = node[0]
        if kind == "int":
            return node[1]
        if kind == "ref":
            return self.cell_value(parse_ref(node[1]))
        if kind == "neg":
            v = self.eval(node[1])
            return v if is_err(v) else -v
        if kind in ("bin", "cmp"):
            a = self.eval(node[2])
            b = self.eval(node[3])
            errs = [v for v in (a, b) if is_err(v)]
            if errs:
                return worst(errs)
            op = node[1]
            if kind == "cmp":
                res = {"=": a == b, "<>": a != b, "<": a < b, ">": a > b,
                       "<=": a <= b, ">=": a >= b}[op]
                return 1 if res else 0
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if b == 0:
                return "#DIV/0!"
            q = trunc_div(a, b)
            return q if op == "/" else a - q * b
        if kind == "if":
            cond = self.eval(node[1])
            if is_err(cond):
                return cond
            return self.eval(node[2] if cond != 0 else node[3])
        if kind == "range_fn":
            name = node[1]
            r1, c1 = parse_ref(node[2])
            r2, c2 = parse_ref(node[3])
            lo_r, hi_r = min(r1, r2), max(r1, r2)
            lo_c, hi_c = min(c1, c2), max(c1, c2)
            present = [(r, c) for r in range(lo_r, hi_r + 1)
                       for c in range(lo_c, hi_c + 1) if (r, c) in self.cells]
            if name == "COUNT":
                return len(present)
            vals = [self.cell_value(rc) for rc in present]
            errs = [v for v in vals if is_err(v)]
            if errs:
                return worst(errs)
            if name == "SUM":
                return sum(vals)
            if not vals:
                return "#REF!"
            return min(vals) if name == "MIN" else max(vals)
        raise ValueError(f"bad node {kind}")


def num_to_col(n):
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def main():
    cells = {}
    with open(sys.argv[1]) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            ref, content = line.split("\t", 1)
            cells[parse_ref(ref)] = content
    sheet = Sheet(cells)
    lines = []
    for rc in sorted(cells):
        v = sheet.cell_value(rc)
        lines.append(f"{num_to_col(rc[1])}{rc[0]}\t{v}")
    with open(sys.argv[2], "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"{len(lines)} cells evaluated")


if __name__ == "__main__":
    main()
