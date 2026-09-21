#!/usr/bin/env bash
# T16-version-bump-consistency checker. cwd = workspace copy, TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

python3 - "$CHECKER_DIR" <<'PYEOF'
import json
import os
import re
import subprocess
import sys

fails = []
task_dir = sys.argv[1]


def sh(*args):
    return subprocess.run(["git"] + list(args), capture_output=True,
                          text=True, check=True).stdout


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def expect(cond, msg):
    if not cond:
        fails.append(msg)


# --- 0. git refs/history must be byte-for-byte the original graph ---------
try:
    expected_refs = json.load(open(os.path.join(task_dir, "expected", "refs.json")))
    expect(sh("rev-parse", "HEAD").strip() == expected_refs["head"],
           "HEAD moved or history was rewritten; leave edits uncommitted")
    expect(sh("rev-parse", "v2.3.0").strip() == expected_refs["tag_object"],
           "annotated v2.3.0 tag object moved or was replaced")
    expect(sh("rev-parse", "v2.3.0^{}").strip() == expected_refs["tag_commit"],
           "v2.3.0 no longer peels to the original commit")
    hashes = sh("log", "--format=%H %ae", "v2.3.0..HEAD").strip().splitlines()
except subprocess.CalledProcessError as e:
    print("FAIL: git log v2.3.0..HEAD failed:", e.stderr.strip())
    sys.exit(1)
expect(len(hashes) == 15,
       f"history changed: {len(hashes)} commits after v2.3.0 (want 15; "
       "do not create commits)")
expect(all(h.endswith(" bench@local") for h in hashes),
       "history changed: found commits not authored by bench@local")

subjects = sh("log", "--reverse", "--format=%s", "v2.3.0..HEAD").strip().splitlines()
want_feats = [s[len("feat: "):] for s in subjects if s.startswith("feat: ")]
want_fixes = [s[len("fix: "):] for s in subjects if s.startswith("fix: ")]

# --- 1. the 10 version locations ------------------------------------------
V = "3.0.0"
expect(os.path.exists("VERSION") and read("VERSION").strip() == V,
       f"VERSION file content must be exactly {V}")

t = read("pyproject.toml")
expect(re.search(r'^version = "3\.0\.0"$', t, re.M),
       'pyproject.toml: need version = "3.0.0"')

t = read("src/lattice_cli/__init__.py")
expect(re.search(r'^__version__ = "3\.0\.0"$', t, re.M),
       'src/lattice_cli/__init__.py: need __version__ = "3.0.0"')

t = read("README.md")
expect("version-3.0.0" in t, "README.md: badge URL not bumped (version-3.0.0)")
expect("lattice-cli==3.0.0" in t, "README.md: install snippet not bumped")

t = read("docs/conf.py")
expect(re.search(r'^version = "3\.0\.0"$', t, re.M), 'docs/conf.py: need version = "3.0.0"')
expect(re.search(r'^release = "3\.0\.0"$', t, re.M), 'docs/conf.py: need release = "3.0.0"')

t = read("CITATION.cff")
expect(re.search(r"^version: 3\.0\.0$", t, re.M), "CITATION.cff: need version: 3.0.0")

t = read("Dockerfile")
expect('version="3.0.0"' in t, 'Dockerfile: need LABEL version="3.0.0"')

t = read("deploy/compose.yaml")
expect("lattice/lattice-cli:3.0.0" in t, "deploy/compose.yaml: image tag not bumped")

t = read("helm/Chart.yaml")
expect(re.search(r"^version: 3\.0\.0$", t, re.M), "helm/Chart.yaml: need version: 3.0.0")
expect(re.search(r'^appVersion: "3\.0\.0"$', t, re.M),
       'helm/Chart.yaml: need appVersion: "3.0.0"')

t = read(".github/workflows/release.yml")
expect(re.search(r'RELEASE_VERSION: "3\.0\.0"', t),
       '.github/workflows/release.yml: need RELEASE_VERSION: "3.0.0"')

# --- 2. no 2.3.0 remnants outside CHANGELOG.md -----------------------------
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
    for fn in files:
        p = os.path.normpath(os.path.join(root, fn))
        if p == "CHANGELOG.md":
            continue
        if "2.3.0" in read(p):
            fails.append(f"remnant 2.3.0 in {p}")

# --- 3. changelog section, validated live against git log ------------------
cl = read("CHANGELOG.md") if os.path.exists("CHANGELOG.md") else ""
expect(cl, "CHANGELOG.md missing")
headings = [m.group(0).strip() for m in re.finditer(r"^## .*$", cl, re.M)]
if not headings or headings[0] != "## 3.0.0":
    fails.append("first '## ' heading in CHANGELOG.md must be '## 3.0.0' "
                 f"(found: {headings[:1]})")
else:
    m = re.search(r"^## 3\.0\.0$(.*?)(?=^## |\Z)", cl, re.M | re.S)
    section = m.group(1)
    fm = re.search(r"^### Features$(.*?)(?=^### |\Z)", section, re.M | re.S)
    xm = re.search(r"^### Fixes$(.*?)(?=^### |\Z)", section, re.M | re.S)
    expect(fm, "3.0.0 section: missing '### Features' subsection")
    expect(xm, "3.0.0 section: missing '### Fixes' subsection")
    if fm and xm:
        got_feats = re.findall(r"^- (.*)$", fm.group(1), re.M)
        got_fixes = re.findall(r"^- (.*)$", xm.group(1), re.M)
        expect(got_feats == want_feats,
               f"Features bullets wrong.\n  got:  {got_feats}\n  want: {want_feats}")
        expect(got_fixes == want_fixes,
               f"Fixes bullets wrong.\n  got:  {got_fixes}\n  want: {want_fixes}")
    stray = re.findall(r"^- .*$", section, re.M)
    n_expected = len(want_feats) + len(want_fixes)
    expect(len(stray) == n_expected,
           f"3.0.0 section has {len(stray)} bullets, want {n_expected} "
           "(chore:/docs: commits must be excluded)")
# old history must survive
expect("## 2.3.0" in cl and "## 2.2.0" in cl,
       "existing CHANGELOG.md history sections were removed")

if fails:
    for msg in fails:
        print(f"FAIL: {msg}")
    sys.exit(1)
print("PASS: all 10 version locations at 3.0.0, no remnants, changelog matches git log")
PYEOF
