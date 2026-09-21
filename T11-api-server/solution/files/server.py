#!/usr/bin/env python3
"""Reference implementation of the Notes API (spec.md). Stdlib only."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit, parse_qs

STATE_FILE = "notes.json"
NOTE_PATH = re.compile(r"^/notes/([0-9]+)$")


class State:
    def __init__(self):
        self.notes = {}  # id -> note dict
        self.next_id = 1

    def load(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
            self.next_id = int(data["next_id"])
            self.notes = {int(n["id"]): n for n in data["notes"]}

    def save(self):
        data = {
            "next_id": self.next_id,
            "notes": [self.notes[i] for i in sorted(self.notes)],
        }
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, STATE_FILE)


STATE = State()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, obj=None):
        body = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(status)
        if obj is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _not_found(self):
        self._send(404, {"error": "not_found"})

    def _bad_request(self):
        self._send(400, {"error": "bad_request"})

    def do_POST(self):
        if urlsplit(self.path).path != "/notes":
            return self._not_found()
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self._bad_request()
        if not isinstance(payload, dict):
            return self._bad_request()
        text = payload.get("text")
        tags = payload.get("tags", [])
        if not isinstance(text, str):
            return self._bad_request()
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return self._bad_request()
        note = {"id": STATE.next_id, "text": text, "tags": tags}
        STATE.notes[note["id"]] = note
        STATE.next_id += 1
        STATE.save()
        self._send(201, note)

    def do_GET(self):
        parts = urlsplit(self.path)
        m = NOTE_PATH.match(parts.path)
        if m:
            note = STATE.notes.get(int(m.group(1)))
            return self._send(200, note) if note else self._not_found()
        if parts.path != "/notes":
            return self._not_found()
        qs = parse_qs(parts.query, keep_blank_values=True)
        limit = 100
        if "limit" in qs:
            try:
                limit = int(qs["limit"][-1], 10)
            except ValueError:
                return self._bad_request()
            limit = max(1, min(100, limit))
        notes = [STATE.notes[i] for i in sorted(STATE.notes)]
        if "tag" in qs:
            tag = qs["tag"][-1]
            notes = [n for n in notes if tag in n["tags"]]
        self._send(200, {"notes": notes[:limit]})

    def do_DELETE(self):
        m = NOTE_PATH.match(urlsplit(self.path).path)
        if not m:
            return self._not_found()
        nid = int(m.group(1))
        if nid not in STATE.notes:
            return self._not_found()
        del STATE.notes[nid]
        STATE.save()
        self._send(204)


def main():
    STATE.load()
    port = int(os.environ.get("BENCH_PORT", "8765"))
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
