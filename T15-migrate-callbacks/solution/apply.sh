#!/usr/bin/env bash
# Reference solution for T15: replace taskflow internals with the asyncio
# migration (errors.py and __init__.py are unchanged by the migration).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/taskflow/source.py" taskflow/source.py
cp "$SCRIPT_DIR/taskflow/transform.py" taskflow/transform.py
cp "$SCRIPT_DIR/taskflow/sink.py" taskflow/sink.py
cp "$SCRIPT_DIR/taskflow/pipeline.py" taskflow/pipeline.py
cp "$SCRIPT_DIR/taskflow/api.py" taskflow/api.py
find taskflow -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
echo "applied asyncio migration to taskflow/"
