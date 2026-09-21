#!/usr/bin/env python3
"""T12-doc-qa-long generator.

Renders fixture/docs/protocol-spec.md (~60KB), fixture/questions.md, and
expected/answers.json + solution/files/answers.json — ALL derived from the
single SPEC dict below, so the document is internally consistent and the
expected answers are computed, never hand-typed.
"""
import json
import os
import random

TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(TASK, "fixture", "docs")
SEED = 730

# ---------------------------------------------------------------- source of truth
SPEC = {
    "name": "LatticeSync",
    "proto_version": "3.2",
    "wire_version": 12,
    "timeouts_ms": {
        "HANDSHAKE_TIMEOUT": ("Maximum time a peer may spend completing the handshake exchange", 4000),
        "HEARTBEAT_INTERVAL": ("Interval at which HEARTBEAT frames are emitted on an open session", 15000),
        "HEARTBEAT_TIMEOUT": ("Elapsed silence after which the HEARTBEAT_TIMEOUT event fires", 45000),
        "RESYNC_STALL_TIMEOUT": ("Maximum time a RESYNC round may make no forward progress", 30000),
        "SESSION_IDLE_TIMEOUT": ("Idle time after which an open session begins draining", 600000),
        "ACK_GRACE_PERIOD": ("Extra time granted for a trailing ACK after a batch boundary", 2500),
    },
    "limits": {
        "MAX_FRAME_BYTES": ("Hard upper bound on the size of one encoded frame, header included", 262144),
        "MAX_INFLIGHT_FRAMES": ("Frames that may be unacknowledged at any moment", 64),
        "MAX_TAG_LENGTH": ("Longest permitted tag, in bytes of UTF-8", 48),
        "MAX_SESSIONS_PER_NODE": ("Concurrent sessions one node may keep open", 128),
        "MAX_DELTA_CHAIN": ("Longest chain of deltas allowed before a checkpoint is required", 512),
    },
    "error_codes": [
        (1000, "OK", "No error; used in CLOSE frames after an orderly shutdown."),
        (4001, "ERR_MALFORMED_FRAME", "The frame could not be decoded (bad magic, truncated header, or CRC mismatch)."),
        (4002, "ERR_FRAME_TOO_LARGE", "The declared frame size exceeds MAX_FRAME_BYTES."),
        (4003, "ERR_UNSUPPORTED_VERSION", "The peer requested a wire version this node does not speak."),
        (4008, "ERR_TAG_TOO_LONG", "A subscription or frame tag exceeds MAX_TAG_LENGTH bytes."),
        (4102, "ERR_CHECKPOINT_MISSING", "A referenced checkpoint id is unknown to the receiving node."),
        (4104, "ERR_DELTA_CHAIN_OVERFLOW", "A delta chain grew past MAX_DELTA_CHAIN without a checkpoint."),
        (5001, "ERR_INTERNAL", "Unrecoverable internal failure; the session is torn down."),
        (5003, "ERR_RESYNC_ABORTED", "A resynchronization round was abandoned (stall or repeated mismatch)."),
    ],
    "states": [
        ("IDLE", "No session exists yet; the node is listening."),
        ("HANDSHAKING", "OPEN_REQUEST received or sent; capability and version exchange in flight."),
        ("READY", "Session established; no bulk transfer in progress."),
        ("SYNCING", "Steady-state delta streaming between the peers."),
        ("RESYNC", "Recovering from divergence by replaying from an agreed checkpoint."),
        ("DRAINING", "No new work is accepted; in-flight frames are being flushed."),
        ("CLOSED", "Terminal state; the session id may never be reused."),
    ],
    # (state, event, guard, next_state, note)
    "transitions": [
        ("IDLE", "OPEN_REQUEST", "-", "HANDSHAKING", "A well-formed OPEN_REQUEST always begins a handshake."),
        ("HANDSHAKING", "HANDSHAKE_ACK", "wire version compatible", "READY", "The session becomes usable."),
        ("HANDSHAKING", "HANDSHAKE_ACK", "wire version incompatible", "CLOSED", "The node answers with ERR_UNSUPPORTED_VERSION."),
        ("HANDSHAKING", "HANDSHAKE_TIMEOUT", "-", "CLOSED", "Fired when HANDSHAKE_TIMEOUT elapses without a HANDSHAKE_ACK."),
        ("READY", "SYNC_BEGIN", "-", "SYNCING", "Either peer may begin a sync round."),
        ("READY", "SESSION_IDLE_TIMEOUT", "-", "DRAINING", "Idle sessions drain instead of closing abruptly."),
        ("READY", "HEARTBEAT_TIMEOUT", "-", "CLOSED", "A silent peer in READY is presumed gone."),
        ("SYNCING", "SYNC_COMPLETE", "-", "READY", "The batch cursor is checkpointed first."),
        ("SYNCING", "CHECKPOINT_MISMATCH", "-", "RESYNC", "Divergent checkpoints force a resynchronization."),
        ("SYNCING", "DELTA_CHAIN_OVERFLOW", "-", "RESYNC", "Reported alongside ERR_DELTA_CHAIN_OVERFLOW."),
        ("SYNCING", "HEARTBEAT_TIMEOUT", "-", "CLOSED", "A silent peer mid-sync is presumed gone."),
        ("RESYNC", "RESYNC_COMPLETE", "checkpoint verified", "SYNCING", "Streaming resumes from the verified checkpoint."),
        ("RESYNC", "RESYNC_STALL_TIMEOUT", "-", "CLOSED", "The node emits ERR_RESYNC_ABORTED before closing."),
        ("RESYNC", "HEARTBEAT_TIMEOUT", "-", "DRAINING", "Unlike READY or SYNCING, a resyncing session drains so partial replay state can be flushed to disk."),
        ("DRAINING", "DRAIN_COMPLETE", "-", "CLOSED", "All in-flight frames were flushed or abandoned."),
        ("DRAINING", "OPEN_REQUEST", "-", "DRAINING", "New work is refused while draining; the request is ignored."),
    ],
    # frame header, field order matters: (name, bytes, description)
    "frame_fields": [
        ("magic", 4, "Constant 0x4C 0x53 0x59 0x4E ('LSYN')."),
        ("wire_version", 2, "Big-endian unsigned; must equal the negotiated wire version."),
        ("flags", 2, "Bit 0 = compressed payload, bit 1 = tagged, bit 2 = checkpoint marker; other bits reserved."),
        ("session_id", 8, "Random 64-bit id chosen by the opening peer."),
        ("sequence", 8, "Monotonic per-session frame counter, starting at 1."),
        ("tag_length", 2, "Byte length of the tag block; 0 when the tagged flag is clear."),
        ("payload_length", 4, "Byte length of the payload that follows the tag block."),
        ("crc32", 4, "CRC-32 (IEEE) over the header bytes preceding this field."),
    ],
    "config": [
        # (name, type, default, range_or_enum, applies_to, note)
        ("sync.batch_size", "int", 32, [1, 256], "sender", "Deltas grouped into one flush before an ACK is expected."),
        ("sync.ack_every", "int", 4, [1, 32], "receiver", "Batches acknowledged with a single cumulative ACK."),
        ("resync.window_frames", "int", 128, [16, 1024], "both", "Frames replayed per resync round; larger windows recover faster but hold more memory."),
        ("resync.max_rounds", "int", 6, [1, 24], "both", "Resync rounds attempted before ERR_RESYNC_ABORTED."),
        ("heartbeat.jitter_pct", "int", 10, [0, 40], "sender", "Random jitter applied to HEARTBEAT_INTERVAL to avoid thundering herds."),
        ("transport.compression", "enum", "lz4", ["none", "lz4", "zstd"], "both", "Codec for payloads when the compressed flag is set."),
        ("transport.nagle", "bool", False, [False, True], "sender", "Whether small frames may be coalesced."),
        ("checkpoint.interval_deltas", "int", 256, [32, 2048], "sender", "Deltas between automatic checkpoint markers; must stay below MAX_DELTA_CHAIN."),
        ("session.max_tags", "int", 32, [1, 512], "both", "Distinct subscription tags one session may hold."),
        ("session.reopen_backoff_ms", "int", 1200, [100, 60000], "client", "Initial backoff after an unexpected CLOSED; doubles per attempt."),
        ("log.frame_sample_rate", "int", 0, [0, 1000], "both", "Per-mille of frames logged verbatim; 0 disables sampling."),
        ("security.require_encryption", "bool", True, [False, True], "server", "Reject peers that do not offer the encrypted-frames feature."),
    ],
    # feature -> (introduced in client, min server version, note)
    "features": [
        ("encrypted-frames", "2.9.0", "3.0.0", "Mandatory when security.require_encryption is true."),
        ("tag-subscriptions", "3.0.0", "3.0.2", "Server-side tag filtering; earlier servers ignore tag blocks."),
        ("delta-compression", "3.1.2", "3.1.0", "Per-delta codec negotiation inside a batch."),
        ("multiplexed-sessions", "3.1.0", "3.1.4", "Several logical sessions over one transport connection."),
        ("partial-checkpoint", "3.2.0", "3.2.1", "Checkpoints covering a tag subset; requires tag-subscriptions."),
    ],
}

# ---------------------------------------------------------------- derived answers
def transition_target(state, event):
    for s, e, _g, nxt, _n in SPEC["transitions"]:
        if s == state and e == event:
            return nxt
    raise KeyError((state, event))


def config_entry(name):
    for row in SPEC["config"]:
        if row[0] == name:
            return row
    raise KeyError(name)


def error_code(sym):
    for code, name, _d in SPEC["error_codes"]:
        if name == sym:
            return code
    raise KeyError(sym)


def feature_min_server(feat):
    for name, _cli, srv, _n in SPEC["features"]:
        if name == feat:
            return srv
    raise KeyError(feat)


HEADER_BYTES = sum(sz for _n, sz, _d in SPEC["frame_fields"])

ANSWERS = {
    "q1": config_entry("resync.window_frames")[2],
    "q2": transition_target("RESYNC", "HEARTBEAT_TIMEOUT"),
    "q3": [error_code("ERR_FRAME_TOO_LARGE"), SPEC["limits"]["MAX_FRAME_BYTES"][1]],
    "q4": feature_min_server("partial-checkpoint"),
    "q5": list(config_entry("sync.batch_size")[3]),
    "q6": SPEC["timeouts_ms"]["RESYNC_STALL_TIMEOUT"][1],
    "q7": transition_target("SYNCING", "CHECKPOINT_MISMATCH"),
    "q8": HEADER_BYTES,
}

# ---------------------------------------------------------------- prose machinery
rng = random.Random(SEED)

CONNECTIVES = [
    "In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything.",
    "Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.",
    "The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below.",
    "Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.",
    "Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.",
    "Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.",
    "The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions.",
    "A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.",
    "All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.",
    "The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries.",
    "Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.",
    "When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.",
    "This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.",
    "The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.",
    "Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports.",
    "Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated.",
]

def paras(n):
    out = []
    for _ in range(n):
        k = rng.randint(2, 3)
        out.append(" ".join(rng.sample(CONNECTIVES, k)))
    return "\n\n".join(out)


L = []  # document lines
def emit(s=""):
    L.append(s)

def table(header, rows):
    emit("| " + " | ".join(header) + " |")
    emit("|" + "|".join(["---"] * len(header)) + "|")
    for r in rows:
        emit("| " + " | ".join(str(c) for c in r) + " |")
    emit()

T = {k: v for k, (_d, v) in SPEC["timeouts_ms"].items()}
LIM = {k: v for k, (_d, v) in SPEC["limits"].items()}

# ---------------------------------------------------------------- render document
emit(f"# {SPEC['name']} v{SPEC['proto_version']} — Synchronization Protocol Specification")
emit()
emit(f"Status: Stable. Wire version: {SPEC['wire_version']}. This document is the sole normative reference for {SPEC['name']} v{SPEC['proto_version']}.")
emit()
emit(paras(2))
emit()

# 1 Overview
emit("## 1. Overview")
emit()
emit(f"{SPEC['name']} is a session-oriented, frame-based synchronization protocol. Two peers open a session, negotiate wire version {SPEC['wire_version']} and a feature set (section 11), and then exchange delta frames grouped into batches. When the peers' checkpoints diverge, the session drops into a dedicated resynchronization mode (section 8) instead of tearing down.")
emit()
emit(paras(3))
emit()

# 2 Terminology
emit("## 2. Terminology and Conventions")
emit()
for term, expl in [
    ("frame", "the atomic wire unit: a fixed header (section 6) followed by an optional tag block and a payload."),
    ("delta", "an application-supplied change record carried as a frame payload."),
    ("batch", "a run of delta frames terminated by a flush; sized by sync.batch_size."),
    ("checkpoint", "a named cut in the delta stream both peers can compare and replay from."),
    ("delta chain", "the run of deltas since the last checkpoint; bounded by MAX_DELTA_CHAIN."),
    ("tag", "a short UTF-8 label used for server-side filtering; bounded by MAX_TAG_LENGTH."),
    ("session", "the long-lived association between exactly two peers, identified by a 64-bit id."),
    ("node", "a process speaking this protocol; one node may hold up to MAX_SESSIONS_PER_NODE sessions."),
]:
    emit(f"- **{term}** — {expl}")
emit()
emit(paras(2))
emit()

# 3 Transport & handshake
emit("## 3. Transport and Handshake")
emit()
emit(f"Sessions run over any ordered, reliable byte stream. The opening peer sends OPEN_REQUEST carrying its wire version and feature list; the responder answers with HANDSHAKE_ACK. The whole exchange must finish within HANDSHAKE_TIMEOUT ({T['HANDSHAKE_TIMEOUT']} ms) or the session is abandoned (see the state machine in section 5).")
emit()
emit(f"A responder that does not speak wire version {SPEC['wire_version']} answers with error {error_code('ERR_UNSUPPORTED_VERSION')} (ERR_UNSUPPORTED_VERSION) and closes. Version negotiation never downgrades below the highest version both peers share.")
emit()
emit(paras(3))
emit()

# 4 Timeouts
emit("## 4. Timeouts and Intervals")
emit()
emit("The following constants govern all timing behaviour. They are protocol constants, not configuration (contrast with section 10).")
emit()
table(["Constant", "Value (ms)", "Meaning"],
      [(k, v, d) for k, (d, v) in SPEC["timeouts_ms"].items()])
emit(f"Heartbeats are emitted every HEARTBEAT_INTERVAL ({T['HEARTBEAT_INTERVAL']} ms), optionally jittered by heartbeat.jitter_pct (section 10). The HEARTBEAT_TIMEOUT event fires after {T['HEARTBEAT_TIMEOUT']} ms of total silence — three missed heartbeats — and its effect depends on the current state (section 5). During resynchronization a separate watchdog applies: if a RESYNC round makes no forward progress for RESYNC_STALL_TIMEOUT ({T['RESYNC_STALL_TIMEOUT']} ms), the round is abandoned with ERR_RESYNC_ABORTED.")
emit()
emit(paras(3))
emit()

# 5 State machine
emit("## 5. Session State Machine")
emit()
emit("A session is always in exactly one of the following states:")
emit()
for name, desc in SPEC["states"]:
    emit(f"- **{name}** — {desc}")
emit()
emit("### 5.1 Transition table")
emit()
emit("Rows not listed are protocol errors: a conforming node receiving an unlisted event in a given state closes the session with ERR_INTERNAL. Guards are evaluated before the transition is taken.")
emit()
table(["Current state", "Event", "Guard", "Next state"],
      [(s, e, g, nxt) for s, e, g, nxt, _ in SPEC["transitions"]])
emit("### 5.2 Transition notes")
emit()
for s, e, g, nxt, note in SPEC["transitions"]:
    guard = "" if g == "-" else f" (guard: {g})"
    emit(f"- **{s} --{e}--> {nxt}**{guard}: {note}")
emit()
emit(paras(3))
emit()

# 6 Frame format
emit("## 6. Frame Format")
emit()
emit("Every frame begins with a fixed header. Multi-byte integers are big-endian and unsigned. The fields appear on the wire in exactly the order of the table below.")
emit()
table(["Field", "Size (bytes)", "Description"],
      [(n, sz, d) for n, sz, d in SPEC["frame_fields"]])
emit(f"The fixed header is therefore {HEADER_BYTES} bytes in total. It is followed by tag_length bytes of tag block and payload_length bytes of payload. The size of the entire encoded frame — header, tag block, and payload together — MUST NOT exceed MAX_FRAME_BYTES ({LIM['MAX_FRAME_BYTES']} bytes); a peer that receives a frame declaring a larger size rejects it with error {error_code('ERR_FRAME_TOO_LARGE')} (ERR_FRAME_TOO_LARGE) without attempting to decode the payload.")
emit()
emit(f"Tags longer than MAX_TAG_LENGTH ({LIM['MAX_TAG_LENGTH']} bytes) are rejected with ERR_TAG_TOO_LONG. At most MAX_INFLIGHT_FRAMES ({LIM['MAX_INFLIGHT_FRAMES']}) frames may be unacknowledged at any time; senders that reach the bound stall until a cumulative ACK arrives.")
emit()
emit(paras(3))
emit()

# 7 Sync
emit("## 7. Steady-State Sync and Delta Chains")
emit()
emit(f"In SYNCING, the sender groups deltas into batches of sync.batch_size (default {config_entry('sync.batch_size')[2]}) and expects a cumulative ACK every sync.ack_every batches. Every checkpoint.interval_deltas deltas the sender injects a checkpoint marker frame (flags bit 2). The chain of deltas since the last checkpoint may never exceed MAX_DELTA_CHAIN ({LIM['MAX_DELTA_CHAIN']}); crossing the bound raises the DELTA_CHAIN_OVERFLOW event and error {error_code('ERR_DELTA_CHAIN_OVERFLOW')} (ERR_DELTA_CHAIN_OVERFLOW), and the session moves to RESYNC as specified in section 5.")
emit()
emit(paras(4))
emit()

# 8 Resync
emit("## 8. Resynchronization")
emit()
emit(f"RESYNC replays frames from the newest checkpoint both peers can verify. Replay proceeds in rounds of resync.window_frames frames (default {config_entry('resync.window_frames')[2]}, allowed range {config_entry('resync.window_frames')[3][0]}..{config_entry('resync.window_frames')[3][1]}). After at most resync.max_rounds rounds without convergence, or when a round stalls for RESYNC_STALL_TIMEOUT ({T['RESYNC_STALL_TIMEOUT']} ms), the node abandons resynchronization with ERR_RESYNC_ABORTED ({error_code('ERR_RESYNC_ABORTED')}).")
emit()
emit("Heartbeats continue during RESYNC. Note the asymmetry called out in section 5: a HEARTBEAT_TIMEOUT during RESYNC does not close the session directly — the session drains first, so partially replayed state reaches disk and a later session can resume from it.")
emit()
emit(paras(3))
emit()

# 9 Error codes
emit("## 9. Error Codes")
emit()
emit("Error codes travel in CLOSE and REJECT frames. Codes 1xxx are informational, 4xxx are peer errors, 5xxx are local failures.")
emit()
table(["Code", "Symbol", "Meaning"], SPEC["error_codes"])
for code, name, desc in SPEC["error_codes"]:
    emit(f"- **{code} {name}** — {desc} {rng.choice(CONNECTIVES)}")
emit()
emit(paras(2))
emit()

# 10 Configuration
emit("## 10. Configuration Parameters")
emit()
emit("Unlike the constants of sections 4 and 6, the parameters below are per-deployment tunables. Defaults are normative: a parameter left unset MUST behave exactly as its default. Ranges are inclusive at both ends; values outside the range are a configuration error and the node refuses to start.")
emit()
table(["Parameter", "Type", "Default", "Allowed values", "Applies to"],
      [(n, t, json.dumps(dflt) if isinstance(dflt, bool) else dflt,
        (str(rv[0]) + ".." + str(rv[1])) if t == "int" else " / ".join(json.dumps(v) if isinstance(v, bool) else v for v in rv),
        who)
       for n, t, dflt, rv, who, _note in SPEC["config"]])
emit("### 10.1 Parameter notes")
emit()
for n, t, dflt, rv, who, note in SPEC["config"]:
    emit(f"- **{n}** — {note} {rng.choice(CONNECTIVES)}")
emit()
emit(paras(2))
emit()

# 11 Compatibility
emit("## 11. Compatibility and Versioning")
emit()
emit("Protocol releases are versioned MAJOR.MINOR.PATCH. Features are negotiated at handshake time by name; a feature is usable on a session only when the client library and the server both meet the versions below. The two columns intentionally differ — client support usually ships first.")
emit()
table(["Feature", "Introduced in client", "Minimum server version", "Notes"], SPEC["features"])
emit(paras(3))
emit()

# 12 Worked examples
emit("## 12. Worked Examples")
emit()
bs = config_entry("sync.batch_size")[2]
ae = config_entry("sync.ack_every")[2]
emit(f"**Example 1 — batching.** With defaults, a sender flushes after every {bs} deltas and expects one cumulative ACK per {ae} batches, i.e. one ACK per {bs*ae} deltas. With MAX_INFLIGHT_FRAMES = {LIM['MAX_INFLIGHT_FRAMES']}, at most {LIM['MAX_INFLIGHT_FRAMES']} of those may be unacknowledged at once, so a default sender stalls after {LIM['MAX_INFLIGHT_FRAMES'] // bs} unacknowledged batches.")
emit()
emit(f"**Example 2 — frame sizing.** A frame carrying a 12-byte tag and a 1000-byte payload occupies {HEADER_BYTES} + 12 + 1000 = {HEADER_BYTES + 12 + 1000} bytes on the wire, comfortably below MAX_FRAME_BYTES ({LIM['MAX_FRAME_BYTES']}). A hypothetical frame declaring payload_length = {LIM['MAX_FRAME_BYTES']} would exceed the bound once the {HEADER_BYTES}-byte header is added and is rejected with ERR_FRAME_TOO_LARGE ({error_code('ERR_FRAME_TOO_LARGE')}).")
emit()
rw = config_entry("resync.window_frames")[2]
mr = config_entry("resync.max_rounds")[2]
emit(f"**Example 3 — resync budget.** With defaults, a resynchronization may replay up to {rw} x {mr} = {rw*mr} frames before ERR_RESYNC_ABORTED ({error_code('ERR_RESYNC_ABORTED')}), and each round has {T['RESYNC_STALL_TIMEOUT']} ms to make progress.")
emit()
bo = config_entry("session.reopen_backoff_ms")[2]
emit(f"**Example 4 — reconnect backoff.** After an unexpected CLOSED, a default client waits {bo} ms, then {bo*2} ms, then {bo*4} ms between attempts, capping at the configured range maximum.")
emit()
emit(paras(3))
emit()
emit("*End of specification.*")

doc = "\n".join(L) + "\n"

# pad with an appendix of consistent per-section commentary until ~60KB
appendix = ["", "## Appendix A. Implementation Notes (non-normative)", ""]
i = 0
while len(doc) + sum(len(x) + 1 for x in appendix) < 60000:
    i += 1
    appendix.append(f"**A.{i}.** " + " ".join(rng.sample(CONNECTIVES, 3)))
    appendix.append("")
doc += "\n".join(appendix) + "\n"

os.makedirs(DOCS, exist_ok=True)
with open(os.path.join(DOCS, "protocol-spec.md"), "w", newline="\n") as f:
    f.write(doc)

# ---------------------------------------------------------------- questions.md
Q = f"""# Questions about docs/protocol-spec.md

Answer every question below using ONLY the specification in docs/protocol-spec.md.
Write the answers to a file named answers.json in the workspace root: a single JSON
object with exactly the keys q1..q8 and the exact value types stated per question.

q1. What is the default value of the configuration parameter `resync.window_frames`?
    Answer format: JSON integer.

q2. Which state does a session enter when a HEARTBEAT_TIMEOUT event fires while the
    session is in the RESYNC state?
    Answer format: JSON string, the state name exactly as written in the spec
    (UPPERCASE).

q3. What numeric error code is returned when an encoded frame exceeds the maximum
    permitted frame size, and what is that maximum size in bytes?
    Answer format: JSON array of exactly two integers: [error_code, max_size_bytes].

q4. According to the compatibility matrix, what is the minimum SERVER version that
    supports the `partial-checkpoint` feature?
    Answer format: JSON string "X.Y.Z" (the version exactly as written).

q5. What is the allowed range (inclusive) of the configuration parameter
    `sync.batch_size`?
    Answer format: JSON array of exactly two integers: [min, max].

q6. What is the value, in milliseconds, of the RESYNC_STALL_TIMEOUT protocol
    constant?
    Answer format: JSON integer.

q7. Which state does a session in SYNCING enter when a CHECKPOINT_MISMATCH event
    occurs?
    Answer format: JSON string, the state name exactly as written in the spec
    (UPPERCASE).

q8. What is the total size, in bytes, of the fixed frame header (the sum of all
    header fields in the frame format table)?
    Answer format: JSON integer.
"""
with open(os.path.join(TASK, "fixture", "questions.md"), "w", newline="\n") as f:
    f.write(Q)

# ---------------------------------------------------------------- answers
for dest in (os.path.join(TASK, "expected"), os.path.join(TASK, "solution", "files")):
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "answers.json"), "w", newline="\n") as f:
        json.dump(ANSWERS, f, indent=2)
        f.write("\n")

print(f"doc bytes: {len(doc)}")
print("answers:", json.dumps(ANSWERS))
