# Document gateway API — specification

Single file server.py (workspace root, Python 3 stdlib only). Binds
127.0.0.1 on port int(os.environ.get("BENCH_PORT", 8765)). In-memory
state; no persistence. All bodies are JSON; all error bodies have
exactly the shape {"error": "<code>"}.

## Authentication and rate limiting (checked FIRST on every request)

- Every request must carry an X-Api-Key header; without it: 401
  {"error": "missing_api_key"} (no token is consumed).
- Per api key: a token bucket, capacity 20 tokens, refill rate 10
  tokens/second (continuous, capped at 20). A bucket starts FULL at its
  key's first request. Each allowed request consumes exactly 1 token.
  If fewer than 1 token: 429 {"error": "rate_limited"} with a
  Retry-After header = the number of seconds until 1 token is available,
  rounded UP to an integer (minimum 1). A 429 consumes nothing.
- Time source: if the request carries an X-Test-Clock header (integer
  milliseconds), that value IS "now" for this request's bucket math.
  Otherwise use wall time. (The grader always sends X-Test-Clock.)

## Endpoints

### POST /docs
Create a document. Body must be a JSON object; else 400
{"error": "bad_request"}. Response 201:
{"id": <int>, "version": 1, "doc": <body>}. ids are sequential from 1.

Idempotency: if an Idempotency-Key header is present:
- first use: store the (key -> response) mapping and reply normally.
- same key + byte-identical body: replay the ORIGINAL response (same
  id, still 201) WITHOUT creating anything.
- same key + different body: 422 {"error": "idempotency_conflict"}.

### GET /docs/{id}
200 {"id", "version", "doc"} with header ETag: "v<version>" (quoted,
e.g. "v3"). If the request has If-None-Match equal to the current ETag:
304 with empty body (ETag header still present). Unknown id: 404
{"error": "not_found"}.

### PUT /docs/{id}
Full replace. Requires header If-Match: "v<version>" (same quoted
format). Missing If-Match: 428 {"error": "precondition_required"}.
Wrong version: 409 {"error": "version_conflict"}. Body not a JSON
object: 400. Success: 200 {"id", "version": <old+1>, "doc": <body>}.
Unknown id: 404.

### DELETE /docs/{id}
204 empty body; unknown id: 404. A deleted id is never reused.

### GET /docs?limit=N&cursor=C
List documents sorted by id ascending:
{"items": [{"id", "version", "doc"}...], "next_cursor": <str or null>}.
- limit: default 10, clamped into [1, 50]; a non-integer limit: 400.
- cursor: opaque; the value is base64("id:<last id of previous page>")
  (standard base64 of that ASCII string). Items strictly after that id.
  An undecodable/malformed cursor: 400.
- next_cursor is null when there are no further items, else the cursor
  for the last returned item.

### Anything else
404 {"error": "not_found"}. Malformed JSON body where an object is
required: 400 {"error": "bad_request"}.

## Misc

- Content-Type of JSON responses: application/json.
- The server keeps running until killed; one request at a time is fine.
