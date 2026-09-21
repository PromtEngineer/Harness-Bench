#!/usr/bin/env bash
set -euo pipefail
export GIT_AUTHOR_NAME="Fix Agent" GIT_AUTHOR_EMAIL="fix@shop.test"
export GIT_COMMITTER_NAME="Fix Agent" GIT_COMMITTER_EMAIL="fix@shop.test"
BAD1=$(sed -n 1p "$TASK_DIR/expected/bad_commits.txt")
BAD2=$(sed -n 2p "$TASK_DIR/expected/bad_commits.txt")
cd webshop
git checkout -q -b fixed feature/pricing-v2
git -c user.name="Fix Agent" -c user.email="fix@shop.test" \
    revert --no-edit "$BAD1" "$BAD2" >/dev/null
cd ..
printf '%s\n%s\n' "$BAD1" "$BAD2" > bad_commits.txt
echo "T31 reference solution applied"
