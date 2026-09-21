#!/usr/bin/env python3
"""Build-time generator for T04-log-extract. Deterministic (seed 74204).

Writes fixture/logs/app.log (~40k lines, ~5 MB) and expected/answer.json.

Planted signal:
- Exactly ONE request_id (the culprit) with 4 status=500 lines on
  path=/api/checkout, all upstream=payments-gateway timeouts.
Near misses:
- Two request_ids with exactly 2 status=500 lines each on /api/checkout
  (one timeout-flavored, one connection-reset-flavored).
- One request_id with 3 status=500 timeout lines on path=/api/cart
  (3+ occurrences but the wrong path).
- Scattered isolated 500/502/503 noise lines, each with a unique request_id
  (so no noise request_id ever exceeds one 500).
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_LOG = os.path.join(ROOT, "fixture", "logs", "app.log")
EXPECTED = os.path.join(ROOT, "expected")

N_LINES = 40000

SERVICES = ["web", "auth", "checkout", "payments", "inventory"]
PATHS = {
    "web": ["/api/products", "/api/search", "/api/home", "/static/bundle.js"],
    "auth": ["/api/login", "/api/token", "/api/logout"],
    "checkout": ["/api/checkout", "/api/cart", "/api/cart/items"],
    "payments": ["/api/pay", "/api/refund"],
    "inventory": ["/api/stock", "/api/stock/reserve"],
}
UPSTREAMS = [
    "payments-gateway", "inventory-db", "auth-idp",
    "shipping-api", "ledger-core", "email-relay",
]
METHODS = ["GET", "POST", "PUT"]
OK_STATUSES = [200, 200, 200, 200, 201, 204]
ERR_STATUSES = [500, 500, 502, 503]
ERR_TEXTS = [
    'error="upstream timeout after 3000ms"',
    'error="connection refused"',
    'error="connection reset by upstream"',
    'error="bad gateway response"',
]

rng = random.Random(74204)
used_ids = set()


def new_id():
    while True:
        rid = "req-" + "".join(rng.choice("0123456789abcdef") for _ in range(8))
        if rid not in used_ids:
            used_ids.add(rid)
            return rid


def ts(i):
    """Monotonic-ish timestamp derived from line index (6h span from 06:00)."""
    total_ms = 6 * 3600 * 1000
    t = int(i * (total_ms / N_LINES))
    h, rem = divmod(t, 3600 * 1000)
    m, rem = divmod(rem, 60 * 1000)
    s, ms = divmod(rem, 1000)
    return f"2026-07-19T{6 + h:02d}:{m:02d}:{s:02d}.{ms:03d}Z"


def client():
    return f"client=10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def info_line(i, service=None, rid=None, path=None, status=None):
    service = service or rng.choice(SERVICES)
    rid = rid or new_id()
    path = path or rng.choice(PATHS[service])
    status = status if status is not None else rng.choice(OK_STATUSES)
    method = rng.choice(METHODS)
    lat = rng.randint(4, 900)
    return (f"{ts(i)} {service} INFO request_id={rid} {client()} method={method} "
            f"path={path} status={status} bytes={rng.randint(120, 48000)} latency_ms={lat}")


def warn_line(i):
    service = rng.choice(SERVICES)
    rid = new_id()
    path = rng.choice(PATHS[service])
    upstream = rng.choice(UPSTREAMS)
    lat = rng.randint(1500, 2900)
    return (f"{ts(i)} {service} WARN request_id={rid} {client()} method={rng.choice(METHODS)} "
            f"path={path} status=200 upstream={upstream} latency_ms={lat} "
            f'warn="upstream latency above threshold"')


def error_line(i, service, rid, path, status, upstream, err_text, lat=None):
    lat = lat if lat is not None else rng.randint(2900, 3400)
    return (f"{ts(i)} {service} ERROR request_id={rid} {client()} method=POST "
            f"path={path} status={status} upstream={upstream} {err_text} latency_ms={lat}")


def noise_error_line(i):
    service = rng.choice(SERVICES)
    rid = new_id()
    path = rng.choice(PATHS[service])
    status = rng.choice(ERR_STATUSES)
    upstream = rng.choice(UPSTREAMS)
    err = rng.choice(ERR_TEXTS)
    return error_line(i, service, rid, path, status, upstream, err)


def main():
    lines = []
    for i in range(N_LINES):
        roll = rng.random()
        if roll < 0.925:
            lines.append(info_line(i))
        elif roll < 0.975:
            lines.append(warn_line(i))
        else:
            lines.append(noise_error_line(i))  # isolated: unique request_id

    timeout = 'error="upstream timeout after 3000ms"'
    reset = 'error="connection reset by upstream"'

    # Culprit: 4 x 500 on /api/checkout, upstream=payments-gateway timeouts,
    # plus two earlier INFO lines for the same request for realism.
    culprit = new_id()
    lines[11894] = info_line(11894, "web", culprit, "/api/products", 200)
    lines[12000] = info_line(12000, "checkout", culprit, "/api/cart", 200)
    for idx in (12518, 18734, 25341, 31262):
        lines[idx] = error_line(idx, "checkout", culprit, "/api/checkout", 500,
                                "payments-gateway", timeout)

    # Near miss A: exactly 2 x 500 on /api/checkout (also payments-gateway timeouts).
    near_a = new_id()
    for idx in (8121, 8987):
        lines[idx] = error_line(idx, "checkout", near_a, "/api/checkout", 500,
                                "payments-gateway", timeout)

    # Near miss B: exactly 2 x 500 on /api/checkout, different upstream/error.
    near_b = new_id()
    for idx in (21400, 22093):
        lines[idx] = error_line(idx, "checkout", near_b, "/api/checkout", 500,
                                "inventory-db", reset)

    # Distractor C: 3 x 500 timeouts, but on path=/api/cart.
    distractor = new_id()
    for idx in (33005, 33780, 34512):
        lines[idx] = error_line(idx, "checkout", distractor, "/api/cart", 500,
                                "inventory-db", timeout)

    os.makedirs(os.path.dirname(FIXTURE_LOG), exist_ok=True)
    with open(FIXTURE_LOG, "w") as f:
        f.write("\n".join(lines) + "\n")

    os.makedirs(EXPECTED, exist_ok=True)
    answer = {
        "request_id": culprit,
        "upstream_service": "payments-gateway",
        "error_count": 4,
    }
    with open(os.path.join(EXPECTED, "answer.json"), "w") as f:
        json.dump(answer, f, indent=2)
        f.write("\n")

    # Sanity: verify the invariant "exactly one request_id with >=3 checkout 500s".
    from collections import Counter
    counts = Counter()
    for line in lines:
        if "status=500" in line and " path=/api/checkout " in line:
            rid = line.split("request_id=")[1].split()[0]
            counts[rid] += 1
    over = [r for r, c in counts.items() if c >= 3]
    assert over == [culprit], f"invariant violated: {over}"
    assert counts[culprit] == 4
    twos = sorted(r for r, c in counts.items() if c == 2)
    assert twos == sorted([near_a, near_b]), twos
    size = os.path.getsize(FIXTURE_LOG)
    print(f"log: {N_LINES} lines, {size / 1e6:.2f} MB; culprit={culprit} "
          f"near_a={near_a} near_b={near_b} distractor={distractor}")


if __name__ == "__main__":
    main()
