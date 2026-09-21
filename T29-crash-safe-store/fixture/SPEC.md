# Crash-safe key-value store — protocol and durability contract

Implement kvstore.py in the workspace root:

    python3 kvstore.py

It speaks a line protocol on stdin/stdout and persists under ./kvdata/
(create the directory if missing; its layout is entirely up to you).

## Protocol

One command per line; one response line per command; FLUSH stdout after
every response. Keys match [A-Za-z0-9_.-]{1,128}. Values travel as
standard base64 (decoded size up to 64 KiB).

    SET <key> <b64value>   ->  OK
    DEL <key>              ->  OK          (also for a missing key)
    GET <key>              ->  VAL <b64>   or  NONE
    DUMPALL                ->  one "ROW <key> <b64>" line per live key,
                               sorted by key, then "END"
    anything else          ->  ERR <reason>   (any reason; keep running)

On EOF on stdin, exit cleanly.

## Durability (the actual task)

The store is graded by being KILLED, hard (SIGKILL), many times:

1. Any SET or DEL that has been acknowledged with OK must survive an
   immediate SIGKILL: reply only AFTER the change is flushed to the OS
   and fsynced. A restart against the same kvdata/ must serve it.
2. A SIGKILL can land mid-write (a command was sent but not yet
   acknowledged). Whether that op survives is up to fate — but the store
   must restart cleanly and every PREVIOUSLY acknowledged op must still
   be intact.
3. Torn trailing writes: after a crash, the grader may append GARBAGE
   BYTES to the most recently modified file under kvdata/. Recovery must
   tolerate a corrupt tail (e.g. frame + checksum your records) without
   losing any acknowledged op and without crashing. A recovered store
   keeps accepting writes, and those must be durable too — think about
   what a corrupt tail in the middle of your file would do to records
   you append after it.
4. Startup with an empty or missing kvdata/ is a valid empty store.

Restarts happen in the same working directory. Performance: hundreds of
ops must complete in seconds, not minutes (fsync per op is fine).
