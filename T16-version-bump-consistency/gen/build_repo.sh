#!/usr/bin/env bash
# Deterministic builder for the T16 lattice-cli fixture repo.
# Run from the task directory:  bash gen/build_repo.sh
set -euo pipefail

TASK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIX="$TASK/fixture"
rm -rf "$FIX"
mkdir -p "$FIX"
cd "$FIX"

git init -q -b main

GITC=(git -c user.name=bench -c user.email=bench@local)

commit() { # commit "<msg>" "<iso date>"
  local msg="$1" when="$2"
  git add -A
  GIT_COMMITTER_DATE="$when" "${GITC[@]}" commit -q --date="$when" -m "$msg"
}

# --- initial scaffold at 2.2.0 --------------------------------------------
mkdir -p src/lattice_cli docs deploy helm .github/workflows

printf '2.2.0\n' > VERSION

cat > pyproject.toml <<'EOF'
[project]
name = "lattice-cli"
version = "2.2.0"
description = "Deterministic environment lattice manager"
requires-python = ">=3.10"

[project.scripts]
lattice = "lattice_cli.cli:main"
EOF

cat > src/lattice_cli/__init__.py <<'EOF'
"""lattice-cli package."""

__version__ = "2.2.0"
EOF

cat > src/lattice_cli/cli.py <<'EOF'
"""Command line entrypoint for lattice-cli."""
import sys

from . import __version__


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--version":
        print(__version__)
        return 0
    if argv and argv[0] == "status":
        print("lattice: ok")
        return 0
    print("usage: lattice [--version|status]")
    return 2
EOF

cat > README.md <<'EOF'
# lattice-cli

![version](https://img.shields.io/badge/version-2.2.0-blue)

Deterministic environment lattice manager.

## Install

```
pip install lattice-cli==2.2.0
```
EOF

cat > docs/conf.py <<'EOF'
project = "lattice-cli"
author = "Lattice Maintainers"
version = "2.2.0"
release = "2.2.0"
extensions = []
EOF

cat > docs/index.md <<'EOF'
# lattice-cli documentation

The lattice command manages deterministic environment lattices.
EOF

cat > CITATION.cff <<'EOF'
cff-version: 1.2.0
title: lattice-cli
version: 2.2.0
date-released: "2026-02-16"
authors:
  - family-names: Bench
    given-names: Builder
EOF

cat > Dockerfile <<'EOF'
FROM python:3.12-slim
LABEL version="2.2.0"
LABEL org.opencontainers.image.title="lattice-cli"
COPY . /app
RUN pip install /app
ENTRYPOINT ["lattice"]
EOF

cat > deploy/compose.yaml <<'EOF'
services:
  lattice:
    image: lattice/lattice-cli:2.2.0
    restart: unless-stopped
EOF

cat > helm/Chart.yaml <<'EOF'
apiVersion: v2
name: lattice-cli
description: Helm chart for lattice-cli
type: application
version: 2.2.0
appVersion: "2.2.0"
EOF

cat > .github/workflows/release.yml <<'EOF'
name: release
on:
  push:
    tags: ["v*"]
env:
  RELEASE_VERSION: "2.2.0"
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "releasing $RELEASE_VERSION"
EOF

cat > Makefile <<'EOF'
.PHONY: test lint
test:
	python3 -m pytest -q
lint:
	python3 -m flake8 src
EOF

cat > CHANGELOG.md <<'EOF'
# Changelog

## 2.2.0

- initial public release
EOF

commit "feat: initial lattice-cli scaffolding" "2026-03-30T10:00:00+00:00"

# --- two more pre-tag commits ---------------------------------------------
cat > src/lattice_cli/sync.py <<'EOF'
"""Sync engine for lattice-cli."""


def sync(profile):
    return {"profile": profile, "synced": True}
EOF
commit "feat: add sync command" "2026-03-31T10:00:00+00:00"

cat >> src/lattice_cli/cli.py <<'EOF'


def load_config(path):
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        return {}
    if not text.strip():
        return {}
    return {"raw": text}
EOF
commit "fix: handle empty config file" "2026-04-01T10:00:00+00:00"

# --- release 2.3.0: bump the 10 version locations + changelog -------------
python3 - <<'EOF'
import re

def sub_file(path, old, new):
    text = open(path).read()
    assert old in text, (path, old)
    open(path, "w").write(text.replace(old, new))

for p in ["VERSION", "pyproject.toml", "src/lattice_cli/__init__.py",
          "README.md", "docs/conf.py", "CITATION.cff", "Dockerfile",
          "deploy/compose.yaml", "helm/Chart.yaml",
          ".github/workflows/release.yml"]:
    sub_file(p, "2.2.0", "2.3.0")

cl = open("CHANGELOG.md").read()
section = ("## 2.3.0\n\n### Features\n\n- add sync command\n\n"
           "### Fixes\n\n- handle empty config file\n\n")
cl = cl.replace("# Changelog\n\n", "# Changelog\n\n" + section, 1)
open("CHANGELOG.md", "w").write(cl)
EOF
commit "chore: release 2.3.0" "2026-04-02T10:00:00+00:00"

GIT_COMMITTER_DATE="2026-04-02T10:05:00+00:00" \
  "${GITC[@]}" tag -a v2.3.0 -m "release 2.3.0"

# --- 15 post-tag commits (5 feat, 6 fix, 4 chore/docs) --------------------
n=0
next_date() { n=$((n+1)); printf '2026-04-%02dT10:00:00+00:00' $((5 + n)); }

cat >> src/lattice_cli/cli.py <<'EOF'


def status_json():
    return '{"status": "ok"}'
EOF
commit "feat: add --json output to status command" "$(next_date)"

cat >> src/lattice_cli/cli.py <<'EOF'


MISSING_MANIFEST_EXIT = 3
EOF
commit "fix: correct exit code on missing manifest" "$(next_date)"

cat > Makefile <<'EOF'
.PHONY: test lint fmt
test:
	python3 -m pytest -q
lint:
	python3 -m flake8 src
fmt:
	python3 -m black src
EOF
commit "chore: tidy Makefile phony targets" "$(next_date)"

cat >> src/lattice_cli/cli.py <<'EOF'


def lattice_home(env):
    return env.get("LATTICE_HOME", "~/.lattice")
EOF
commit "feat: support LATTICE_HOME override" "$(next_date)"

cat >> src/lattice_cli/sync.py <<'EOF'


def quote_path(path):
    return '"%s"' % path if " " in path else path
EOF
commit "fix: quote paths with spaces in runner" "$(next_date)"

cat >> docs/index.md <<'EOF'

## Sync workflow

Run `lattice sync <profile>` to reconcile the local lattice.
EOF
commit "docs: document the sync workflow" "$(next_date)"

cat >> src/lattice_cli/sync.py <<'EOF'


class StateFile:
    def __init__(self):
        self.closed = False

    def close(self):
        if not self.closed:
            self.closed = True
EOF
commit "fix: avoid double-close of state file" "$(next_date)"

cat >> src/lattice_cli/cli.py <<'EOF'


def prune(keep):
    return {"pruned": True, "keep": keep}
EOF
commit "feat: add prune subcommand" "$(next_date)"

cat > .flake8 <<'EOF'
[flake8]
max-line-length = 100
EOF
commit "chore: bump dev lint config" "$(next_date)"

cat >> src/lattice_cli/sync.py <<'EOF'


def with_retry(fn, attempts=3):
    for i in range(attempts):
        try:
            return fn()
        except OSError:
            if i == attempts - 1:
                raise
EOF
commit "fix: retry transient lock errors in sync" "$(next_date)"

cat >> src/lattice_cli/cli.py <<'EOF'


def colorize(line):
    if line.startswith("+"):
        return "\033[32m%s\033[0m" % line
    if line.startswith("-"):
        return "\033[31m%s\033[0m" % line
    return line
EOF
commit "feat: colorize diff output" "$(next_date)"

cat > docs/troubleshooting.md <<'EOF'
# Troubleshooting

- If sync hangs, remove the stale lock under the lattice home.
- Re-run with LATTICE_DEBUG=1 for verbose logs.
EOF
commit "docs: add troubleshooting section" "$(next_date)"

cat >> src/lattice_cli/sync.py <<'EOF'


def normalize_manifest(text):
    return text.replace("\r\n", "\n")
EOF
commit "fix: normalize CRLF in imported manifests" "$(next_date)"

cat > src/lattice_cli/completion.py <<'EOF'
"""Shell completion generator."""

BASH_TEMPLATE = "complete -W 'status sync prune' lattice"


def generate(shell):
    if shell == "bash":
        return BASH_TEMPLATE
    raise ValueError("unsupported shell: %s" % shell)
EOF
commit "feat: add shell completion generator" "$(next_date)"

cat >> src/lattice_cli/cli.py <<'EOF'


def validate_retention(days):
    if days < 0:
        raise ValueError("retention must be >= 0")
    return days
EOF
commit "fix: reject negative retention values" "$(next_date)"

echo "--- built. post-tag commits:"
git log --oneline v2.3.0..HEAD | wc -l
git log --reverse --format='%s' v2.3.0..HEAD
echo "--- files containing 2.3.0:"
grep -rl "2.3.0" . --exclude-dir=.git | sort
