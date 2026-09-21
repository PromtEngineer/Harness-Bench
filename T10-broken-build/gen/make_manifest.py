#!/usr/bin/env python3
"""Build-time helper: record sha256 of protected fixture files (tests/, wheels/)."""
import hashlib
import os

TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(TASK, "fixture")
OUT = os.path.join(TASK, "expected", "protected.sha256")

entries = []
for sub in ("tests", "wheels"):
    root = os.path.join(FIX, sub)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, FIX)
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            entries.append(f"{h}  {rel}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="\n") as f:
    f.write("\n".join(entries) + "\n")
print(f"wrote {OUT} ({len(entries)} files)")
