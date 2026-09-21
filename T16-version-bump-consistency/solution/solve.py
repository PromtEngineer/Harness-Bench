#!/usr/bin/env python3
"""Reference solution for T16-version-bump-consistency. cwd = workspace."""
import re
import subprocess

FILES = [
    "VERSION",
    "pyproject.toml",
    "src/lattice_cli/__init__.py",
    "README.md",
    "docs/conf.py",
    "CITATION.cff",
    "Dockerfile",
    "deploy/compose.yaml",
    "helm/Chart.yaml",
    ".github/workflows/release.yml",
]

for p in FILES:
    text = open(p).read()
    assert "2.3.0" in text, p
    open(p, "w").write(text.replace("2.3.0", "3.0.0"))

subjects = subprocess.run(
    ["git", "log", "--reverse", "--format=%s", "v2.3.0..HEAD"],
    capture_output=True, text=True, check=True).stdout.strip().splitlines()
feats = [s[len("feat: "):] for s in subjects if s.startswith("feat: ")]
fixes = [s[len("fix: "):] for s in subjects if s.startswith("fix: ")]

section = "## 3.0.0\n\n### Features\n\n"
section += "".join(f"- {s}\n" for s in feats)
section += "\n### Fixes\n\n"
section += "".join(f"- {s}\n" for s in fixes)
section += "\n"

cl = open("CHANGELOG.md").read()
m = re.search(r"^## ", cl, re.M)
assert m, "no existing ## heading in CHANGELOG.md"
cl = cl[:m.start()] + section + cl[m.start():]
open("CHANGELOG.md", "w").write(cl)
print(f"bumped {len(FILES)} files; changelog: {len(feats)} features, {len(fixes)} fixes")
