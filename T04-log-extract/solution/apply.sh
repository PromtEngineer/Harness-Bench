#!/usr/bin/env bash
# Reference solution for T04-log-extract. cwd = workspace copy.
set -euo pipefail
python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/files/solve.py"
