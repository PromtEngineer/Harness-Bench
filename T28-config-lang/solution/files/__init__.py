"""CONFL configuration language. See SPEC.md for the authoritative spec."""
import json
import os
import re


class ConflError(Exception):
    pass


_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_PATH_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_ENTRY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(\+=|=)\s*(.*)$")
_INCLUDE_RE = re.compile(r'include\s+"([^"]+)"\s*$')
_INT_RE = re.compile(r"-?[0-9]+$")


class _ValueParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def value(self):
        self.ws()
        if self.i >= len(self.s):
            raise ConflError("missing value")
        ch = self.s[self.i]
        if ch == '"':
            return self.string()
        if ch == "r" and self.i + 1 < len(self.s) and self.s[self.i + 1] == '"':
            return self.raw()
        if ch == "[":
            return self.list_()
        return self.atom()

    def string(self):
        self.i += 1
        parts = []
        lit = []

        def flush():
            if lit:
                parts.append(("lit", "".join(lit)))
                del lit[:]

        while True:
            if self.i >= len(self.s):
                raise ConflError("unterminated string")
            ch = self.s[self.i]
            if ch == '"':
                self.i += 1
                flush()
                return ("str", parts)
            if ch == "\\":
                if self.i + 1 >= len(self.s):
                    raise ConflError("unterminated string")
                esc = self.s[self.i + 1]
                if esc == "n":
                    lit.append("\n")
                elif esc == "t":
                    lit.append("\t")
                elif esc == '"':
                    lit.append('"')
                elif esc == "\\":
                    lit.append("\\")
                elif esc == "x":
                    hx = self.s[self.i + 2:self.i + 4]
                    if len(hx) != 2 or any(c not in "0123456789abcdefABCDEF"
                                           for c in hx):
                        raise ConflError(f"bad escape \\x{hx}")
                    lit.append(chr(int(hx, 16)))
                    self.i += 2
                else:
                    raise ConflError(f"bad escape \\{esc}")
                self.i += 2
                continue
            if ch == "$" and self.i + 1 < len(self.s) and self.s[self.i + 1] == "{":
                end = self.s.find("}", self.i + 2)
                if end < 0:
                    raise ConflError("unterminated interpolation")
                path = self.s[self.i + 2:end]
                if not _PATH_RE.match(path):
                    raise ConflError(f"bad interpolation path: {path!r}")
                flush()
                parts.append(("ref", path))
                self.i = end + 1
                continue
            lit.append(ch)
            self.i += 1

    def raw(self):
        self.i += 2
        end = self.s.find('"', self.i)
        if end < 0:
            raise ConflError("unterminated raw string")
        out = self.s[self.i:end]
        self.i = end + 1
        return ("raw", out)

    def list_(self):
        self.i += 1
        items = []
        while True:
            self.ws()
            if self.i >= len(self.s):
                raise ConflError("unterminated list")
            if self.s[self.i] == "]":
                self.i += 1
                return ("list", items)
            items.append(self.value())
            self.ws()
            if self.i < len(self.s) and self.s[self.i] == ",":
                self.i += 1
                continue
            if self.i < len(self.s) and self.s[self.i] == "]":
                self.i += 1
                return ("list", items)
            raise ConflError("expected ',' or ']' in list")

    def atom(self):
        j = self.i
        while j < len(self.s) and self.s[j] not in " \t,]":
            j += 1
        tok = self.s[self.i:j]
        self.i = j
        if tok == "true":
            return ("bool", True)
        if tok == "false":
            return ("bool", False)
        if _INT_RE.match(tok):
            return ("int", int(tok))
        raise ConflError(f"bad value {tok!r}")


def _parse_value(text):
    p = _ValueParser(text)
    v = p.value()
    p.ws()
    if p.i != len(p.s):
        raise ConflError(f"trailing characters after value: {p.s[p.i:]!r}")
    return v


def _strip_comment(line):
    i = 0
    state = "normal"
    while i < len(line):
        ch = line[i]
        if state == "normal":
            if ch == "#":
                return line[:i]
            if ch == '"':
                prev = line[i - 1] if i > 0 else ""
                prev2 = line[i - 2] if i > 1 else ""
                if prev == "r" and not (prev2.isalnum() or prev2 == "_"):
                    state = "raw"
                else:
                    state = "str"
        elif state == "str":
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = "normal"
        elif state == "raw":
            if ch == '"':
                state = "normal"
        i += 1
    return line


def _parse_file(path, entries, order, depth, stack):
    if depth > 8:
        raise ConflError("include depth limit exceeded")
    real = os.path.realpath(path)
    if real in stack:
        raise ConflError(f"include cycle: {os.path.basename(path)}")
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError:
        raise ConflError(f"cannot read file: {path}")
    stack.append(real)
    section = ""
    for lineno, rawline in enumerate(text.splitlines(), 1):
        line = _strip_comment(rawline).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1].strip()
            if not _PATH_RE.match(sec):
                raise ConflError(f"bad section header: {line}")
            section = sec
            continue
        m = _INCLUDE_RE.match(line)
        if m:
            inc = os.path.join(os.path.dirname(path), m.group(1))
            _parse_file(inc, entries, order, depth + 1, stack)
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            raise ConflError(f"bad line {lineno}: {line!r}")
        key, op, rhs = m.groups()
        full = f"{section}.{key}" if section else key
        tree = _parse_value(rhs)
        if op == "=":
            if full not in entries:
                order.append(full)
            entries[full] = tree
        else:
            if full not in entries:
                raise ConflError(f"append to undefined key: {full}")
            old = entries[full]
            if old[0] == "list" and tree[0] == "list":
                entries[full] = ("list", old[1] + tree[1])
            elif old[0] in ("str", "raw") and tree[0] in ("str", "raw"):
                def as_parts(t):
                    return t[1] if t[0] == "str" else [("lit", t[1])]
                entries[full] = ("str", as_parts(old) + as_parts(tree))
            else:
                raise ConflError(
                    f"cannot append {tree[0]} to {old[0]} at {full}")
    stack.pop()


def load(path):
    """Parse and fully resolve a CONFL file into a nested dict."""
    entries = {}
    order = []
    _parse_file(path, entries, order, 0, [])

    resolved = {}
    resolving = []

    def render(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        if isinstance(v, str):
            return v
        raise ConflError("cannot interpolate list")

    def resolve(p):
        if p in resolved:
            return resolved[p]
        if p in resolving:
            chain = resolving[resolving.index(p):] + [p]
            raise ConflError("interpolation cycle: " + " -> ".join(chain))
        resolving.append(p)
        try:
            resolved[p] = res_tree(entries[p])
        finally:
            resolving.pop()
        return resolved[p]

    def res_tree(tree):
        kind, val = tree
        if kind in ("int", "bool", "raw"):
            return val
        if kind == "str":
            out = []
            for pk, pv in val:
                if pk == "lit":
                    out.append(pv)
                else:
                    if pv not in entries:
                        raise ConflError(f"unknown key in interpolation: {pv}")
                    out.append(render(resolve(pv)))
            return "".join(out)
        return [res_tree(t) for t in val]

    for p in order:
        resolve(p)

    root = {}
    for p in order:
        segs = p.split(".")
        cur = root
        for depth_i, s in enumerate(segs[:-1]):
            if s in cur and not isinstance(cur[s], dict):
                raise ConflError(
                    f"path conflict: {'.'.join(segs[:depth_i + 1])}")
            cur = cur.setdefault(s, {})
        last = segs[-1]
        if last in cur and isinstance(cur[last], dict):
            raise ConflError(f"path conflict: {p}")
        cur[last] = resolved[p]
    return root


def dumps_flat(cfg):
    """Render a nested config dict as sorted 'path=json' lines."""
    lines = []

    def walk(prefix, node):
        if isinstance(node, dict):
            for k in sorted(node):
                walk(f"{prefix}.{k}" if prefix else k, node[k])
        else:
            lines.append(f"{prefix}={json.dumps(node, separators=(',', ':'))}")

    walk("", cfg)
    return "\n".join(lines)
