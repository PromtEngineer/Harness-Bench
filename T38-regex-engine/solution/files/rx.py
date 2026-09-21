"""Thompson-NFA regex engine (subset). See SPEC.md. No `re` anywhere."""


class PatternError(Exception):
    pass


DIGITS = set("0123456789")
WORD = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
SPACE = set(" \t\n\r\f\v")
META = set(".*+?|()[]\\")


class _Parser:
    """pattern -> AST: ("lit", set) ("any",) ("cat", [..]) ("alt", [..])
    ("star", n) ("plus", n) ("opt", n) ("empty",)"""

    def __init__(self, pat):
        self.p = pat
        self.i = 0

    def error(self, msg):
        raise PatternError(f"{msg} at position {self.i}")

    def parse(self):
        node = self.alternation()
        if self.i != len(self.p):
            self.error(f"unexpected {self.p[self.i]!r}")
        return node

    def alternation(self):
        branches = [self.concat()]
        while self.i < len(self.p) and self.p[self.i] == "|":
            self.i += 1
            branches.append(self.concat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def concat(self):
        parts = []
        while self.i < len(self.p) and self.p[self.i] not in "|)":
            parts.append(self.quantified())
        if not parts:
            return ("empty",)
        return parts[0] if len(parts) == 1 else ("cat", parts)

    def quantified(self):
        atom = self.atom()
        if self.i < len(self.p) and self.p[self.i] in "*+?":
            q = self.p[self.i]
            self.i += 1
            if self.i < len(self.p) and self.p[self.i] in "*+?":
                self.error(f"double quantifier {self.p[self.i]!r}")
            return {"*": ("star", atom), "+": ("plus", atom),
                    "?": ("opt", atom)}[q]
        return atom

    def atom(self):
        if self.i >= len(self.p):
            self.error("unexpected end of pattern")
        ch = self.p[self.i]
        if ch in "*+?":
            self.error(f"quantifier {ch!r} with nothing to repeat")
        if ch == "(":
            self.i += 1
            node = self.alternation()
            if self.i >= len(self.p) or self.p[self.i] != ")":
                self.error("unbalanced '('")
            self.i += 1
            return node
        if ch == ")":
            self.error("unbalanced ')'")
        if ch == "[":
            return self.charclass()
        if ch == ".":
            self.i += 1
            return ("any",)
        if ch == "\\":
            return ("lit", self.escape())
        self.i += 1
        return ("lit", {ch})

    def escape(self):
        self.i += 1
        if self.i >= len(self.p):
            self.error("trailing backslash")
        e = self.p[self.i]
        self.i += 1
        if e == "d":
            return set(DIGITS)
        if e == "w":
            return set(WORD)
        if e == "s":
            return set(SPACE)
        if e in META:
            return {e}
        self.error(f"bad escape \\{e}")

    def charclass(self):
        self.i += 1
        negate = False
        if self.i < len(self.p) and self.p[self.i] == "^":
            negate = True
            self.i += 1
        chars = set()
        first = True
        while True:
            if self.i >= len(self.p):
                self.error("unterminated character class")
            ch = self.p[self.i]
            if ch == "]" and not first:
                self.i += 1
                break
            first = False
            if ch == "\\":
                chars |= self.escape()
                continue
            if (self.i + 2 < len(self.p) and self.p[self.i + 1] == "-"
                    and self.p[self.i + 2] != "]"):
                lo, hi = ch, self.p[self.i + 2]
                if ord(lo) > ord(hi):
                    self.error(f"bad range {lo}-{hi}")
                chars |= {chr(c) for c in range(ord(lo), ord(hi) + 1)}
                self.i += 3
                continue
            chars.add(ch)
            self.i += 1
        if not chars:
            self.error("empty character class")
        return ("negcls", chars) if negate else ("lit", chars)


class _NFA:
    """States: list of dicts. Transitions: ("eps", to) or (charset, to);
    charset None means any-char."""

    def __init__(self):
        self.trans = []

    def state(self):
        self.trans.append([])
        return len(self.trans) - 1

    def add(self, frm, label, to):
        self.trans[frm].append((label, to))

    def build(self, node, start):
        """Wire node from `start`; return accept state."""
        kind = node[0]
        if kind == "empty":
            return start
        if kind == "lit":
            end = self.state()
            self.add(start, ("set", node[1]), end)
            return end
        if kind == "negcls":
            end = self.state()
            self.add(start, ("neg", node[1]), end)
            return end
        if kind == "any":
            end = self.state()
            self.add(start, ("any", None), end)
            return end
        if kind == "cat":
            cur = start
            for part in node[1]:
                cur = self.build(part, cur)
            return cur
        if kind == "alt":
            end = self.state()
            for br in node[1]:
                s = self.state()
                self.add(start, ("eps", None), s)
                a = self.build(br, s)
                self.add(a, ("eps", None), end)
            return end
        if kind == "star":
            hub = self.state()
            self.add(start, ("eps", None), hub)
            inner = self.state()
            self.add(hub, ("eps", None), inner)
            a = self.build(node[1], inner)
            self.add(a, ("eps", None), hub)
            return hub
        if kind == "plus":
            a = self.build(node[1], start)
            hub = self.state()
            self.add(a, ("eps", None), hub)
            inner = self.state()
            self.add(hub, ("eps", None), inner)
            b = self.build(node[1], inner)
            self.add(b, ("eps", None), hub)
            return hub
        if kind == "opt":
            end = self.state()
            s = self.state()
            self.add(start, ("eps", None), s)
            a = self.build(node[1], s)
            self.add(a, ("eps", None), end)
            self.add(start, ("eps", None), end)
            return end
        raise PatternError(f"bad node {kind}")


def _compile(pattern):
    ast = _Parser(pattern).parse()
    nfa = _NFA()
    start = nfa.state()
    accept = nfa.build(ast, start)
    return nfa, start, accept


def _closure(nfa, states):
    out = set(states)
    todo = list(states)
    while todo:
        s = todo.pop()
        for label, to in nfa.trans[s]:
            if label[0] == "eps" and to not in out:
                out.add(to)
                todo.append(to)
    return out


def _step(nfa, states, ch):
    nxt = set()
    for s in states:
        for label, to in nfa.trans[s]:
            kind, data = label
            if kind == "set" and ch in data:
                nxt.add(to)
            elif kind == "neg" and ch not in data:
                nxt.add(to)
            elif kind == "any":
                nxt.add(to)
    return nxt


def fullmatch(pattern, text):
    """True iff the whole text matches the pattern."""
    nfa, start, accept = _compile(pattern)
    cur = _closure(nfa, {start})
    for ch in text:
        cur = _closure(nfa, _step(nfa, cur, ch))
        if not cur:
            return False
    return accept in cur


def search(pattern, text):
    """Leftmost-LONGEST match extent as (start, end), or None.

    The empty match counts: pattern a* on "bbb" -> (0, 0).
    """
    nfa, start, accept = _compile(pattern)
    for begin in range(len(text) + 1):
        cur = _closure(nfa, {start})
        best = begin if accept in cur else None
        for pos in range(begin, len(text)):
            cur = _closure(nfa, _step(nfa, cur, text[pos]))
            if not cur:
                break
            if accept in cur:
                best = pos + 1
        if best is not None:
            return (begin, best)
    return None
