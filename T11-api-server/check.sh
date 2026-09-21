#!/usr/bin/env bash
# T11-api-server checker.
# cwd = copy of the workspace after the agent ran; TASK_DIR = task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

SRV1=""
SRV2=""
cleanup() {
  [ -n "$SRV1" ] && kill "$SRV1" 2>/dev/null
  [ -n "$SRV2" ] && kill "$SRV2" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

[ -f server.py ] || fail "server.py not found in workspace"

python3 - <<'PY' || fail "spec.md was modified"
import hashlib
from pathlib import Path

expected = "55b15d7e690b0e0e0e7ef92fc087c476e93c34158d1ce0752cc3293f661494cf"
if hashlib.sha256(Path("spec.md").read_bytes()).hexdigest() != expected:
    raise SystemExit(1)
PY

BODY="$(pwd)/.check_body.$$"
HDRS="$(pwd)/.check_hdrs.$$"

free_port() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'
}

# req METHOD PATH [JSON_BODY] -> sets STATUS, body in $BODY, headers in $HDRS
req() {
  local method="$1" path="$2" data="${3:-}"
  if [ -n "$data" ]; then
    STATUS=$(curl -s -o "$BODY" -D "$HDRS" -w '%{http_code}' -X "$method" \
      -H 'Content-Type: application/json' --data-binary "$data" \
      "http://127.0.0.1:$PORT$path")
  else
    STATUS=$(curl -s -o "$BODY" -D "$HDRS" -w '%{http_code}' -X "$method" \
      "http://127.0.0.1:$PORT$path")
  fi
}

# jassert PYTHON_EXPR  (o = parsed JSON body)
jassert() {
  python3 - "$BODY" "$1" <<'PY'
import json, sys
try:
    o = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"body is not valid JSON: {e}", file=sys.stderr)
    sys.exit(1)
sys.exit(0 if eval(sys.argv[2], {"o": o}) else 1)
PY
}

expect() {  # expect DESC WANT_STATUS [JEXPR]
  local desc="$1" want="$2" jexpr="${3:-}"
  [ "$STATUS" = "$want" ] || fail "$desc: expected HTTP $want, got $STATUS (body: $(head -c 200 "$BODY" 2>/dev/null))"
  if [ -n "$jexpr" ]; then
    jassert "$jexpr" || fail "$desc: body check failed: $jexpr (body: $(head -c 200 "$BODY" 2>/dev/null))"
  fi
}

start_server() {  # start_server LOGFILE -> sets SPID
  env -u TASK_DIR BENCH_PORT="$PORT" python3 server.py >"$1" 2>&1 &
  SPID=$!
  local i=0
  while [ $i -lt 40 ]; do
    if ! kill -0 "$SPID" 2>/dev/null; then
      cat "$1" >&2
      fail "server process exited during startup"
    fi
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/notes"; then
      return 0
    fi
    sleep 0.25
    i=$((i + 1))
  done
  cat "$1" >&2
  fail "server did not become ready within 10s on port $PORT"
}

rm -f notes.json

# ---------- phase 1: fresh server ----------
PORT=$(free_port)
start_server server_check1.log
SRV1=$SPID

req POST /notes '{"text":"buy milk","tags":["errand","home"]}'
expect "POST first note" 201 'o == {"id":1,"text":"buy milk","tags":["errand","home"]}'

req POST /notes '{"text":"ship report","tags":["work"]}'
expect "POST second note" 201 'o["id"] == 2'

req POST /notes '{"text":"call plumber"}'
expect "POST note without tags" 201 'o == {"id":3,"text":"call plumber","tags":[]}'

req GET /notes/1
expect "GET /notes/1" 200 'o == {"id":1,"text":"buy milk","tags":["errand","home"]}'
grep -i '^content-type:' "$HDRS" | grep -qi 'application/json' \
  || fail "GET /notes/1: Content-Type is not application/json"

req GET /notes/99
expect "GET unknown id" 404 'o == {"error":"not_found"}'

req GET /notes/abc
expect "GET non-numeric id" 404 'o == {"error":"not_found"}'

req GET /notes
expect "GET all notes" 200 '[n["id"] for n in o["notes"]] == [1,2,3]'

req GET '/notes?tag=work'
expect "GET tag=work" 200 '[n["id"] for n in o["notes"]] == [2]'

req POST /notes '{"text":"standup notes","tags":["work","meeting"]}'
expect "POST fourth note" 201 'o["id"] == 4'

req GET '/notes?tag=work'
expect "GET tag=work after add" 200 '[n["id"] for n in o["notes"]] == [2,4]'

req GET '/notes?tag=work&limit=1'
expect "GET tag=work limit=1" 200 '[n["id"] for n in o["notes"]] == [2]'

req GET '/notes?limit=0'
expect "GET limit=0 clamps to 1" 200 '[n["id"] for n in o["notes"]] == [1]'

req GET '/notes?limit=500'
expect "GET limit=500 clamps to 100" 200 '[n["id"] for n in o["notes"]] == [1,2,3,4]'

req GET '/notes?limit=abc'
expect "GET non-integer limit" 400 'o == {"error":"bad_request"}'

req POST /notes '{"text": '
expect "POST malformed JSON" 400 'o == {"error":"bad_request"}'

req POST /notes '{"tags":["x"]}'
expect "POST missing text" 400 'o == {"error":"bad_request"}'

req POST /notes '{"text":"t","tags":"work"}'
expect "POST tags not an array" 400 'o == {"error":"bad_request"}'

req DELETE /notes/2
[ "$STATUS" = "204" ] || fail "DELETE /notes/2: expected 204, got $STATUS"
[ -s "$BODY" ] && fail "DELETE /notes/2: body must be empty on 204"

req DELETE /notes/2
expect "second DELETE same id" 404 'o == {"error":"not_found"}'

req GET /notes/2
expect "GET deleted note" 404 'o == {"error":"not_found"}'

req GET '/notes?tag=work'
expect "GET tag=work after delete" 200 '[n["id"] for n in o["notes"]] == [4]'

[ -f notes.json ] || fail "notes.json not written to the working directory after mutations"
python3 -c 'import json; json.load(open("notes.json"))' 2>/dev/null \
  || fail "notes.json is not valid JSON"

req POST /notes '{"text":"after delete","tags":[]}'
expect "id counter not reused after delete" 201 'o["id"] == 5'

# ---------- phase 2: restart, persistence ----------
kill "$SRV1" 2>/dev/null
wait "$SRV1" 2>/dev/null
SRV1=""

PORT=$(free_port)
start_server server_check2.log
SRV2=$SPID

req GET /notes/1
expect "restart: note 1 survived" 200 'o == {"id":1,"text":"buy milk","tags":["errand","home"]}'

req GET /notes/2
expect "restart: deletion persisted" 404 'o == {"error":"not_found"}'

req GET /notes
expect "restart: full list" 200 '[n["id"] for n in o["notes"]] == [1,3,4,5]'

req POST /notes '{"text":"post-restart","tags":["fresh"]}'
expect "restart: id counter persisted" 201 'o["id"] == 6'

kill "$SRV2" 2>/dev/null
wait "$SRV2" 2>/dev/null
SRV2=""

rm -f "$BODY" "$HDRS"
echo "PASS: all API and persistence checks succeeded"
exit 0
