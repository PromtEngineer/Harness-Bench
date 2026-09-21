"""AST -> stack IR.

Ops (op, arg):
    ("PUSH", n)     push integer
    ("LOAD", name)  push variable
    ("STORE", name) pop into variable
    ("ADD"|"SUB"|"MUL"|"DIV"|"MOD", None)   pop b, pop a, push a OP b
    ("LT"|"GT"|"LE"|"GE"|"EQ"|"NE", None)   comparisons -> 1/0
    ("NEG", None)   pop a, push -a
    ("PRINT", None) pop and print
    ("POP", None)   pop and discard
    ("JZ", label)   pop; jump if zero
    ("JMP", label)
    ("LABEL", label)
"""

_BIN = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
        "<": "LT", ">": "GT", "<=": "LE", ">=": "GE", "==": "EQ",
        "!=": "NE"}


class Gen:
    def __init__(self):
        self.ir = []
        self.n = 0

    def label(self):
        self.n += 1
        return f"L{self.n}"

    def expr(self, node):
        kind = node[0]
        if kind == "num":
            self.ir.append(("PUSH", node[1]))
        elif kind == "var":
            self.ir.append(("LOAD", node[1]))
        elif kind == "neg":
            self.expr(node[1])
            self.ir.append(("NEG", None))
        elif kind == "bin":
            self.expr(node[2])
            self.expr(node[3])
            self.ir.append((_BIN[node[1]], None))
        else:
            raise ValueError(kind)

    def stmt(self, node):
        kind = node[0]
        if kind == "block":
            for s in node[1]:
                self.stmt(s)
        elif kind == "let":
            self.expr(node[2])
            self.ir.append(("STORE", node[1]))
        elif kind == "print":
            self.expr(node[1])
            self.ir.append(("PRINT", None))
        elif kind == "if":
            l_else, l_end = self.label(), self.label()
            self.expr(node[1])
            self.ir.append(("JZ", l_else))
            self.stmt(node[2])
            self.ir.append(("JMP", l_end))
            self.ir.append(("LABEL", l_else))
            self.stmt(node[3])
            self.ir.append(("LABEL", l_end))
        else:
            raise ValueError(kind)


def generate(ast):
    g = Gen()
    g.stmt(ast)
    return g.ir
