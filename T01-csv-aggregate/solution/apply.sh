#!/usr/bin/env bash
# Reference solution for T01-csv-aggregate. cwd = workspace copy.
set -euo pipefail
python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/files/solve.py"
