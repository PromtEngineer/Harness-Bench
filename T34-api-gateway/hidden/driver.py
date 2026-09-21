#!/usr/bin/env python3
"""T34 grading driver. Run from the workspace root. Exit 0 = pass."""
import base64
import http.client
import json
import os
import socket
import subprocess
import sys
import time


def fail(msg):
    print(f"DRIVER FAIL: {msg}")
    sys.exit(1)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = free_port()
proc = subprocess.Popen([sys.executable, "server.py"],
                        env=dict(os.environ, BENCH_PORT=str(PORT)),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

CLOCK = [1_000_000]  # ms; advanced explicitly


def req(method, path, body=None, key="main", clock=True, extra=None,
        advance=1000):
    if advance and clock:
        CLOCK[0] += advance
    headers = {}
    if key is not None:
        headers["X-Api-Key"] = key
    if clock:
        headers["X-Test-Clock"] = str(CLOCK[0])
    if extra:
        headers.update(extra)
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, str)) else json.dumps(body)
        headers["Content-Type"] = "application/json"
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=15)
    try:
        conn.request(method, path, body=data, headers=headers)
        r = conn.getresponse()
        raw = r.read()
        hdrs = {k.lower(): v for k, v in r.getheaders()}
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = None
        return r.status, parsed, hdrs, raw
    finally:
        conn.close()


# wait for readiness
deadline = time.time() + 30
while True:
    try:
        st, *_ = req("GET", "/docs")
        break
    except (ConnectionRefusedError, OSError):
        if time.time() > deadline:
            proc.kill()
            fail("server did not become ready within 30s")
        time.sleep(0.3)

try:
    # ---- auth
    st, body, h, _ = req("GET", "/docs", key=None)
    assert st == 401 and body == {"error": "missing_api_key"}, \
        f"401 contract: {st} {body}"

    # ---- create + ETag + 304
    st, d1, h, _ = req("POST", "/docs", {"title": "first", "n": 1})
    assert st == 201 and d1["id"] == 1 and d1["version"] == 1, (st, d1)
    assert d1["doc"] == {"title": "first", "n": 1}, d1
    st, d2, h, _ = req("POST", "/docs", {"title": "second"})
    assert st == 201 and d2["id"] == 2, "ids must be sequential from 1"
    st, got, h, _ = req("GET", "/docs/1")
    assert st == 200 and h.get("etag") == '"v1"', (st, h.get("etag"))
    st, got, h, raw = req("GET", "/docs/1", extra={"If-None-Match": '"v1"'})
    assert st == 304 and raw == b"", f"304 contract: {st} {raw!r}"
    st, got, h, _ = req("GET", "/docs/1", extra={"If-None-Match": '"v9"'})
    assert st == 200, "stale If-None-Match must return 200"
    st, got, *_ = req("GET", "/docs/999")
    assert st == 404 and got == {"error": "not_found"}, (st, got)

    # ---- optimistic concurrency
    st, got, *_ = req("PUT", "/docs/1", {"title": "x"})
    assert st == 428 and got == {"error": "precondition_required"}, (st, got)
    st, got, *_ = req("PUT", "/docs/1", {"title": "x"},
                      extra={"If-Match": '"v2"'})
    assert st == 409 and got == {"error": "version_conflict"}, (st, got)
    st, got, *_ = req("PUT", "/docs/1", {"title": "updated"},
                      extra={"If-Match": '"v1"'})
    assert st == 200 and got["version"] == 2, (st, got)
    st, got, h, _ = req("GET", "/docs/1")
    assert h.get("etag") == '"v2"' and got["doc"] == {"title": "updated"}
    st, got, *_ = req("PUT", "/docs/1", "not json{",
                      extra={"If-Match": '"v2"'})
    assert st == 400 and got == {"error": "bad_request"}, (st, got)
    st, got, *_ = req("PUT", "/docs/999", {"a": 1},
                      extra={"If-Match": '"v1"'})
    assert st == 404, "PUT on unknown id must 404"

    # ---- idempotency
    payload = {"kind": "invoice", "amount": 950}
    st, ida, *_ = req("POST", "/docs", payload,
                      extra={"Idempotency-Key": "k-123"})
    assert st == 201, st
    st, idb, *_ = req("POST", "/docs", payload,
                      extra={"Idempotency-Key": "k-123"})
    assert st == 201 and idb["id"] == ida["id"], \
        f"idempotent replay must return the SAME id: {ida} vs {idb}"
    st, got, *_ = req("POST", "/docs", {"kind": "invoice", "amount": 951},
                      extra={"Idempotency-Key": "k-123"})
    assert st == 422 and got == {"error": "idempotency_conflict"}, (st, got)
    st, nxt, *_ = req("POST", "/docs", {"fresh": True})
    assert nxt["id"] == ida["id"] + 1, \
        "idempotent replay must not consume ids"

    # ---- malformed create
    st, got, *_ = req("POST", "/docs", "{broken")
    assert st == 400 and got == {"error": "bad_request"}, (st, got)
    st, got, *_ = req("POST", "/docs", "[1,2]")
    assert st == 400, "non-object JSON body must 400"

    # ---- delete
    st, _, h, raw = req("DELETE", "/docs/2")
    assert st == 204 and raw == b"", (st, raw)
    st, *_ = req("DELETE", "/docs/2")
    assert st == 404, "second DELETE must 404"
    st, *_ = req("GET", "/docs/2")
    assert st == 404

    # ---- pagination
    for i in range(22):
        st, *_ = req("POST", "/docs", {"seq": i})
        assert st == 201
    st, page, *_ = req("GET", "/docs?limit=10")
    assert st == 200 and len(page["items"]) == 10, page
    ids = [it["id"] for it in page["items"]]
    assert ids == sorted(ids), "list must be sorted by id"
    assert page["next_cursor"], "next_cursor expected"
    dec = base64.b64decode(page["next_cursor"]).decode()
    assert dec == f"id:{ids[-1]}", f"cursor encoding contract: {dec!r}"
    seen = list(ids)
    cur = page["next_cursor"]
    while cur:
        st, page, *_ = req("GET", f"/docs?limit=10&cursor={cur}")
        assert st == 200, st
        seen += [it["id"] for it in page["items"]]
        cur = page["next_cursor"]
    assert seen == sorted(seen) and len(seen) == len(set(seen)), \
        "cursor walk must cover each doc exactly once, ordered"
    st, allp, *_ = req("GET", "/docs?limit=50")
    assert len(allp["items"]) == len(seen) or allp["next_cursor"], allp
    st, got, *_ = req("GET", "/docs?limit=abc")
    assert st == 400, "non-integer limit must 400"
    st, got, *_ = req("GET", "/docs?limit=99")
    assert st == 200 and len(got["items"]) <= 50, "limit must clamp to 50"
    st, got, *_ = req("GET", "/docs?cursor=!!!notb64!!!")
    assert st == 400, "malformed cursor must 400"
    st, got, *_ = req("GET", "/docs?limit=0")
    assert st == 200 and len(got["items"]) == 1, "limit 0 must clamp to 1"

    # ---- rate limiting with the test clock
    RL = "ratelimit-key"
    base = 5_000_000
    for i in range(20):
        st, *_ = req("GET", "/docs?limit=1", key=RL, advance=0,
                     extra={"X-Test-Clock": str(base)}, clock=False)
        assert st == 200, f"warm burst req {i}: {st}"
    st, got, h, _ = req("GET", "/docs?limit=1", key=RL, advance=0,
                        extra={"X-Test-Clock": str(base)}, clock=False)
    assert st == 429 and got == {"error": "rate_limited"}, (st, got)
    assert h.get("retry-after") == "1", \
        f"Retry-After must be 1 (ceil of 0.1s), got {h.get('retry-after')!r}"
    # +500ms -> 5 tokens
    ok = 0
    for i in range(6):
        st, *_ = req("GET", "/docs?limit=1", key=RL, advance=0,
                     extra={"X-Test-Clock": str(base + 500)}, clock=False)
        if st == 200:
            ok += 1
        else:
            assert st == 429, st
    assert ok == 5, f"after 500ms exactly 5 tokens must be available, got {ok}"
    # +10s -> full bucket again (capped at 20)
    ok = 0
    for i in range(25):
        st, *_ = req("GET", "/docs?limit=1", key=RL, advance=0,
                     extra={"X-Test-Clock": str(base + 11_000)}, clock=False)
        if st == 200:
            ok += 1
    assert ok == 20, f"bucket must refill to exactly capacity 20, got {ok}"
    # other keys unaffected
    st, *_ = req("GET", "/docs?limit=1")
    assert st == 200, "main key must be unaffected by ratelimit-key's bucket"

    print("DRIVER PASS")
finally:
    proc.kill()
    proc.wait()
