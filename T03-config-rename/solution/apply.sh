#!/usr/bin/env bash
# Reference solution for T03-config-rename. cwd = workspace copy.
# Renames Orion -> Nova in the six user-facing files; leaves vendor/ and
# tests/ untouched.
set -euo pipefail
python3 - <<'EOF'
files = [
    "src/app/config.py",
    "src/app/cli.py",
    "pyproject.toml",
    "docs/README.md",
    "docs/guide.md",
    "deploy/compose.yaml",
]
for path in files:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace("Orion", "Nova"))
print("renamed Orion -> Nova in", len(files), "files")
EOF
