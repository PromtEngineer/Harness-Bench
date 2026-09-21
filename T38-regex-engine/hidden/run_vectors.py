#!/usr/bin/env python3
"""T38 vector runner + `re` ban scan. argv: <workspace> <vectors.json>"""
import ast
import json
import os
import sys

ws, vec_path = sys.argv[1], sys.argv[2]

# 1. AST-scan every .py in the workspace for re/regex imports
for root, dirs, files in os.walk(ws):
    dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
    for name in files:
        if not name.endswith(".py"):
            continue
        path = os.path.join(root, name)
        try:
            tree = ast.parse(open(path, encoding="utf-8",
                                  errors="replace").read())
        except SyntaxError as exc:
            print(f"VECTOR FAIL: {path} is not valid Python: {exc}")
            sys.exit(1)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            if any(m in ("re", "regex") for m in mods):
                print(f"VECTOR FAIL: {path} imports a banned regex module")
                sys.exit(1)
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "__import__"):
                print(f"VECTOR FAIL: {path} uses dynamic __import__")
                sys.exit(1)
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "import_module"):
                print(f"VECTOR FAIL: {path} uses dynamic import_module")
                sys.exit(1)
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "sys" and node.attr == "modules"):
                print(f"VECTOR FAIL: {path} accesses sys.modules")
                sys.exit(1)

sys.path.insert(0, ws)
import rx  # noqa: E402

vec = json.load(open(vec_path))

def fail(msg):
    print(f"VECTOR FAIL: {msg}")
    sys.exit(1)

for pat, text, want in vec["fullmatch"]:
    try:
        got = rx.fullmatch(pat, text)
    except Exception as exc:
        fail(f"fullmatch({pat!r}, {text!r}) raised {type(exc).__name__}: {exc}")
    if bool(got) != want:
        fail(f"fullmatch({pat!r}, {text!r}) = {got}, expected {want}")

for pat, text, want in vec["search"]:
    want_t = tuple(want) if want else None
    try:
        got = rx.search(pat, text)
    except Exception as exc:
        fail(f"search({pat!r}, {text!r}) raised {type(exc).__name__}: {exc}")
    got_t = tuple(got) if got is not None else None
    if got_t != want_t:
        fail(f"search({pat!r}, {text!r}) = {got_t}, expected {want_t}")

for pat in vec["errors"]:
    try:
        rx.fullmatch(pat, "x")
        fail(f"malformed pattern {pat!r} did not raise rx.PatternError")
    except rx.PatternError:
        pass
    except Exception as exc:
        fail(f"malformed pattern {pat!r} raised {type(exc).__name__}, "
             f"expected rx.PatternError")

n = len(vec["fullmatch"]) + len(vec["search"]) + len(vec["errors"])
print(f"ALL {n} VECTORS PASS")
