# Notes API — server specification (v1)

Implement this API as a single file `server.py` in the workspace root, runnable as:

    python3 server.py

Constraints:

- Python 3.10+ **standard library only** (e.g. `http.server`, `socketserver`, `json`, `urllib.parse`). No third-party packages.
- Bind to host `127.0.0.1`. The port comes from the environment variable `BENCH_PORT`; if it is unset, use `8765`.
- Handling requests sequentially is fine; no concurrency is required.
- The process must keep running until killed and must be restartable immediately (use `http.server.HTTPServer`, which sets `SO_REUSEADDR`, or set it yourself).

## Data model

A note is a JSON object with exactly these keys:

    {"id": <int>, "text": <string>, "tags": [<string>, ...]}

IDs are assigned by the server: sequential integers starting at 1, strictly increasing, **never reused** — not after a DELETE and not after a server restart.

All JSON responses must have `Content-Type: application/json`. The two error bodies are exactly:

    {"error": "not_found"}      (with status 404)
    {"error": "bad_request"}    (with status 400)

## Endpoints

### POST /notes

Request body: JSON object `{"text": <string>, "tags": [<string>, ...]}`. `tags` is optional and defaults to `[]`.

- Body does not parse as JSON, is not an object, `text` is missing or not a string, or `tags` is present but not an array of strings → `400 {"error":"bad_request"}`.
- Success → status `201`, body = the complete stored note, e.g. `{"id": 1, "text": "buy milk", "tags": ["errand"]}`.

### GET /notes/<id>

- `<id>` is a decimal integer naming an existing note → `200` with the note as body.
- Anything else (unknown id, deleted note, non-numeric id) → `404 {"error":"not_found"}`.

### GET /notes[?tag=<t>][&limit=<n>]

Returns `200 {"notes": [<note>, ...]}` — notes ordered by `id` ascending.

- `tag=<t>`: keep only notes whose `tags` array contains exactly `<t>`.
- `limit=<n>`: `<n>` must parse as a base-10 integer, otherwise → `400 {"error":"bad_request"}`. Integer values are clamped into the range 1..100 (so `limit=0` behaves as 1, `limit=500` behaves as 100). When `limit` is absent, it defaults to 100. The limit is applied after tag filtering, keeping the first `<n>` notes in id order.

### DELETE /notes/<id>

- Existing note → status `204` with an **empty** body; the note is removed.
- Unknown/already-deleted/non-numeric id → `404 {"error":"not_found"}` (so deleting the same id twice gives 204 then 404).

### Anything else

Any other path or method → `404 {"error":"not_found"}`.

## Persistence

- After **every successful mutation** (POST or DELETE), the server writes its full state to the file `notes.json` in the current working directory. The file layout is up to you, but it must contain everything needed to restore the server: all live notes **and** the id counter.
- On startup, if `notes.json` exists, the server loads its state from it; otherwise it starts empty with the next id being 1.
- A server that is killed and started again in the same directory must therefore see all notes that existed at the time of the last mutation, and must continue assigning ids where it left off.
