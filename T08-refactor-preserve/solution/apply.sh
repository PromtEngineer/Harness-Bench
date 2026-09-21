#!/usr/bin/env bash
# cwd = workspace copy. Applies the reference refactor.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/files/src/parsing.py" src/parsing.py
cp "$SCRIPT_DIR/files/src/validation.py" src/validation.py
cp "$SCRIPT_DIR/files/src/rendering.py" src/rendering.py
cp "$SCRIPT_DIR/files/src/megamodule.py" src/megamodule.py
