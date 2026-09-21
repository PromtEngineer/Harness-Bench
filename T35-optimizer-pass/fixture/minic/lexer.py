"""MiniExpr lexer."""
import re

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>\d+)
  | (?P<kw>\blet\b|\bprint\b|\bif\b|\belse\b)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|==|!=|[-+*/%<>=;{}()])
""", re.VERBOSE)


def tokenize(src):
    out = []
    pos = 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f"bad character {src[pos]!r} at {pos}")
        pos = m.end()
        if m.lastgroup == "ws":
            continue
        out.append((m.lastgroup, m.group()))
    out.append(("eof", ""))
    return out
