#!/usr/bin/env python3
"""Document gateway per spec.md."""
import base64
import json
import math
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

DOCS = {}
NEXT_ID = [1]
IDEMP = {}
BUCKETS = {}
CAP, RATE = 20.0, 10.0


def bucket_check(key, now_s):
    tokens, last = BUCKETS.get(key, (CAP, now_s))
    tokens = min(CAP, tokens + (now_s - last) * RATE)
    if tokens >= 1.0:
        BUCKETS[key] = (tokens - 1.0, now_s)
        return True, 0
    BUCKETS[key] = (tokens, now_s)
    need = (1.0 - tokens) / RATE
    return False, max(1, math.ceil(need))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _json(self, code, obj, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, code, headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def _gate(self):
        key = self.headers.get("X-Api-Key")
        if not key:
            self._json(401, {"error": "missing_api_key"})
            return False
        clock = self.headers.get("X-Test-Clock")
        now_s = int(clock) / 1000.0 if clock is not None else time.time()
        ok, retry = bucket_check(key, now_s)
        if not ok:
            self._json(429, {"error": "rate_limited"},
                       {"Retry-After": str(retry)})
            return False
        return True

    def _doc_id(self, path):
        try:
            return int(path.split("/docs/", 1)[1])
        except (IndexError, ValueError):
            return None

    def do_POST(self):
        if not self._gate():
            return
        path = self.path.split("?")[0]
        if path != "/docs":
            self._json(404, {"error": "not_found"})
            return
        raw = self._body()
        ikey = self.headers.get("Idempotency-Key")
        if ikey and ikey in IDEMP:
            prev_raw, prev_resp = IDEMP[ikey]
            if prev_raw == raw:
                self._json(201, prev_resp)
            else:
                self._json(422, {"error": "idempotency_conflict"})
            return
        try:
            doc = json.loads(raw)
            assert isinstance(doc, dict)
        except Exception:
            self._json(400, {"error": "bad_request"})
            return
        did = NEXT_ID[0]
        NEXT_ID[0] += 1
        DOCS[did] = {"version": 1, "doc": doc}
        resp = {"id": did, "version": 1, "doc": doc}
        if ikey:
            IDEMP[ikey] = (raw, resp)
        self._json(201, resp)

    def do_GET(self):
        if not self._gate():
            return
        path, _, query = self.path.partition("?")
        if path == "/docs":
            params = {}
            for part in query.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v
            limit = params.get("limit", "10")
            try:
                limit = int(limit)
            except ValueError:
                self._json(400, {"error": "bad_request"})
                return
            limit = max(1, min(50, limit))
            after = 0
            if "cursor" in params:
                try:
                    decoded = base64.b64decode(params["cursor"],
                                               validate=True).decode()
                    if not decoded.startswith("id:"):
                        raise ValueError
                    after = int(decoded[3:])
                except Exception:
                    self._json(400, {"error": "bad_request"})
                    return
            ids = sorted(i for i in DOCS if i > after)
            page = ids[:limit]
            items = [{"id": i, "version": DOCS[i]["version"],
                      "doc": DOCS[i]["doc"]} for i in page]
            if page and ids[len(page):]:
                nxt = base64.b64encode(f"id:{page[-1]}".encode()).decode()
            else:
                nxt = None
            self._json(200, {"items": items, "next_cursor": nxt})
            return
        did = self._doc_id(path)
        if did is None or did not in DOCS:
            self._json(404, {"error": "not_found"})
            return
        etag = f'"v{DOCS[did]["version"]}"'
        if self.headers.get("If-None-Match") == etag:
            self._empty(304, {"ETag": etag})
            return
        self._json(200, {"id": did, "version": DOCS[did]["version"],
                         "doc": DOCS[did]["doc"]}, {"ETag": etag})

    def do_PUT(self):
        if not self._gate():
            return
        did = self._doc_id(self.path.split("?")[0])
        raw = self._body()
        if did is None or did not in DOCS:
            self._json(404, {"error": "not_found"})
            return
        im = self.headers.get("If-Match")
        if im is None:
            self._json(428, {"error": "precondition_required"})
            return
        if im != f'"v{DOCS[did]["version"]}"':
            self._json(409, {"error": "version_conflict"})
            return
        try:
            doc = json.loads(raw)
            assert isinstance(doc, dict)
        except Exception:
            self._json(400, {"error": "bad_request"})
            return
        DOCS[did] = {"version": DOCS[did]["version"] + 1, "doc": doc}
        self._json(200, {"id": did, "version": DOCS[did]["version"],
                         "doc": doc})

    def do_DELETE(self):
        if not self._gate():
            return
        did = self._doc_id(self.path.split("?")[0])
        if did is None or did not in DOCS:
            self._json(404, {"error": "not_found"})
            return
        del DOCS[did]
        self._empty(204)


def main():
    port = int(os.environ.get("BENCH_PORT", 8765))
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
