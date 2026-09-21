"""MiniExpr parser -> AST.

Statements: let NAME = expr ;   print expr ;   if expr { ... } else { ... }
Expressions: ints, names, unary -, + - * / %, comparisons < > <= >= == !=.
"""
from .lexer import tokenize


class Parser:
    def __init__(self, src):
        self.toks = tokenize(src)
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def take(self, kind=None, value=None):
        k, v = self.toks[self.i]
        if (kind and k != kind) or (value and v != value):
            raise SyntaxError(f"expected {kind or value}, got {k} {v!r}")
        self.i += 1
        return v

    def program(self):
        stmts = []
        while self.peek()[0] != "eof":
            stmts.append(self.statement())
        return ("block", stmts)

    def statement(self):
        k, v = self.peek()
        if v == "let":
            self.take(value="let")
            name = self.take("name")
            self.take(value="=")
            expr = self.expr()
            self.take(value=";")
            return ("let", name, expr)
        if v == "print":
            self.take(value="print")
            expr = self.expr()
            self.take(value=";")
            return ("print", expr)
        if v == "if":
            self.take(value="if")
            cond = self.expr()
            self.take(value="{")
            then = []
            while self.peek()[1] != "}":
                then.append(self.statement())
            self.take(value="}")
            other = []
            if self.peek()[1] == "else":
                self.take(value="else")
                self.take(value="{")
                while self.peek()[1] != "}":
                    other.append(self.statement())
                self.take(value="}")
            return ("if", cond, ("block", then), ("block", other))
        raise SyntaxError(f"unexpected {v!r}")

    def expr(self):
        return self.comparison()

    def comparison(self):
        left = self.additive()
        while self.peek()[1] in ("<", ">", "<=", ">=", "==", "!="):
            op = self.take()
            left = ("bin", op, left, self.additive())
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
        k, v = self.peek()
        if k == "num":
            self.take()
            return ("num", int(v))
        if k == "name":
            self.take()
            return ("var", v)
        if v == "(":
            self.take()
            e = self.expr()
            self.take(value=")")
            return e
        raise SyntaxError(f"unexpected {v!r} in expression")


def parse(src):
    return Parser(src).program()
