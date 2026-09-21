#!/usr/bin/env bash
# Checker for T31-git-surgery. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -d webshop/.git ] || fail "webshop/.git is missing"
[ -f bad_commits.txt ] || fail "bad_commits.txt is missing"

BAD1=$(sed -n 1p "$CHECKER_DIR/expected/bad_commits.txt")
BAD2=$(sed -n 2p "$CHECKER_DIR/expected/bad_commits.txt")
MAIN=$(cat "$CHECKER_DIR/expected/main_tip.txt")
FEAT=$(cat "$CHECKER_DIR/expected/feature_tip.txt")

# 1. bad_commits.txt: exactly the two SHAs, any order
GOT=$(tr -d '[:space:]' < bad_commits.txt)
WANT1="$BAD1$BAD2"; WANT2="$BAD2$BAD1"
if ! printf '%s' "$GOT" | grep -qiE "^($WANT1|$WANT2)$"; then
  fail "bad_commits.txt does not name exactly the two regression commits"
fi

cd webshop
# 2. branches intact, fixed exists and contains main's history
git rev-parse -q --verify fixed >/dev/null || fail "branch 'fixed' does not exist"
[ "$(git rev-parse main)" = "$MAIN" ] || fail "main was moved or rewritten"
[ "$(git rev-parse feature/pricing-v2)" = "$FEAT" ] \
  || fail "feature/pricing-v2 was moved or rewritten"
git merge-base --is-ancestor "$MAIN" fixed \
  || fail "'fixed' does not contain main's history"

# 3. check out 'fixed' in a scratch worktree and grade there
WT="$(mktemp -d /tmp/t31-wt-XXXXXX)"
trap 'git worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"' EXIT
git worktree add -q --detach "$WT" fixed || fail "cannot check out 'fixed'"
cd "$WT"

python3 - "$CHECKER_DIR/expected/tests.sha256" <<'PYEOF' || exit 1
import hashlib, pathlib, sys
want = pathlib.Path(sys.argv[1]).read_text().strip().splitlines()
paths = sorted([f"tests/{p.name}" for p in pathlib.Path("tests").glob("*.py")]
               + ["conftest.py"])
have = ["%s  %s" % (hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(), p)
        for p in paths]
if sorted(have) != sorted(want):
    print("CHECK FAIL: tests/ or conftest.py differ on the fixed branch",
          file=sys.stderr)
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || exit 1

timeout 120 python3 -m pytest -q -p no:cacheprovider tests/ \
  || fail "visible tests fail on 'fixed'"
timeout 120 python3 -m pytest -q -p no:cacheprovider "$CHECKER_DIR/hidden" \
  || fail "hidden feature-completeness tests fail on 'fixed'"
echo "CHECK PASS"
exit 0
