# LatticeSync v3.2 — Synchronization Protocol Specification

Status: Stable. Wire version: 12. This document is the sole normative reference for LatticeSync v3.2.

Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

## 1. Overview

LatticeSync is a session-oriented, frame-based synchronization protocol. Two peers open a session, negotiate wire version 12 and a feature set (section 11), and then exchange delta frames grouped into batches. When the peers' checkpoints diverge, the session drops into a dedicated resynchronization mode (section 8) instead of tearing down.

A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated.

The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

## 2. Terminology and Conventions

- **frame** — the atomic wire unit: a fixed header (section 6) followed by an optional tag block and a payload.
- **delta** — an application-supplied change record carried as a frame payload.
- **batch** — a run of delta frames terminated by a flush; sized by sync.batch_size.
- **checkpoint** — a named cut in the delta stream both peers can compare and replay from.
- **delta chain** — the run of deltas since the last checkpoint; bounded by MAX_DELTA_CHAIN.
- **tag** — a short UTF-8 label used for server-side filtering; bounded by MAX_TAG_LENGTH.
- **session** — the long-lived association between exactly two peers, identified by a 64-bit id.
- **node** — a process speaking this protocol; one node may hold up to MAX_SESSIONS_PER_NODE sessions.

The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.

A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

## 3. Transport and Handshake

Sessions run over any ordered, reliable byte stream. The opening peer sends OPEN_REQUEST carrying its wire version and feature list; the responder answers with HANDSHAKE_ACK. The whole exchange must finish within HANDSHAKE_TIMEOUT (4000 ms) or the session is abandoned (see the state machine in section 5).

A responder that does not speak wire version 12 answers with error 4003 (ERR_UNSUPPORTED_VERSION) and closes. Version negotiation never downgrades below the highest version both peers share.

Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

## 4. Timeouts and Intervals

The following constants govern all timing behaviour. They are protocol constants, not configuration (contrast with section 10).

| Constant | Value (ms) | Meaning |
|---|---|---|
| HANDSHAKE_TIMEOUT | 4000 | Maximum time a peer may spend completing the handshake exchange |
| HEARTBEAT_INTERVAL | 15000 | Interval at which HEARTBEAT frames are emitted on an open session |
| HEARTBEAT_TIMEOUT | 45000 | Elapsed silence after which the HEARTBEAT_TIMEOUT event fires |
| RESYNC_STALL_TIMEOUT | 30000 | Maximum time a RESYNC round may make no forward progress |
| SESSION_IDLE_TIMEOUT | 600000 | Idle time after which an open session begins draining |
| ACK_GRACE_PERIOD | 2500 | Extra time granted for a trailing ACK after a batch boundary |

Heartbeats are emitted every HEARTBEAT_INTERVAL (15000 ms), optionally jittered by heartbeat.jitter_pct (section 10). The HEARTBEAT_TIMEOUT event fires after 45000 ms of total silence — three missed heartbeats — and its effect depends on the current state (section 5). During resynchronization a separate watchdog applies: if a RESYNC round makes no forward progress for RESYNC_STALL_TIMEOUT (30000 ms), the round is abandoned with ERR_RESYNC_ABORTED.

The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

## 5. Session State Machine

A session is always in exactly one of the following states:

- **IDLE** — No session exists yet; the node is listening.
- **HANDSHAKING** — OPEN_REQUEST received or sent; capability and version exchange in flight.
- **READY** — Session established; no bulk transfer in progress.
- **SYNCING** — Steady-state delta streaming between the peers.
- **RESYNC** — Recovering from divergence by replaying from an agreed checkpoint.
- **DRAINING** — No new work is accepted; in-flight frames are being flushed.
- **CLOSED** — Terminal state; the session id may never be reused.

### 5.1 Transition table

Rows not listed are protocol errors: a conforming node receiving an unlisted event in a given state closes the session with ERR_INTERNAL. Guards are evaluated before the transition is taken.

| Current state | Event | Guard | Next state |
|---|---|---|---|
| IDLE | OPEN_REQUEST | - | HANDSHAKING |
| HANDSHAKING | HANDSHAKE_ACK | wire version compatible | READY |
| HANDSHAKING | HANDSHAKE_ACK | wire version incompatible | CLOSED |
| HANDSHAKING | HANDSHAKE_TIMEOUT | - | CLOSED |
| READY | SYNC_BEGIN | - | SYNCING |
| READY | SESSION_IDLE_TIMEOUT | - | DRAINING |
| READY | HEARTBEAT_TIMEOUT | - | CLOSED |
| SYNCING | SYNC_COMPLETE | - | READY |
| SYNCING | CHECKPOINT_MISMATCH | - | RESYNC |
| SYNCING | DELTA_CHAIN_OVERFLOW | - | RESYNC |
| SYNCING | HEARTBEAT_TIMEOUT | - | CLOSED |
| RESYNC | RESYNC_COMPLETE | checkpoint verified | SYNCING |
| RESYNC | RESYNC_STALL_TIMEOUT | - | CLOSED |
| RESYNC | HEARTBEAT_TIMEOUT | - | DRAINING |
| DRAINING | DRAIN_COMPLETE | - | CLOSED |
| DRAINING | OPEN_REQUEST | - | DRAINING |

### 5.2 Transition notes

- **IDLE --OPEN_REQUEST--> HANDSHAKING**: A well-formed OPEN_REQUEST always begins a handshake.
- **HANDSHAKING --HANDSHAKE_ACK--> READY** (guard: wire version compatible): The session becomes usable.
- **HANDSHAKING --HANDSHAKE_ACK--> CLOSED** (guard: wire version incompatible): The node answers with ERR_UNSUPPORTED_VERSION.
- **HANDSHAKING --HANDSHAKE_TIMEOUT--> CLOSED**: Fired when HANDSHAKE_TIMEOUT elapses without a HANDSHAKE_ACK.
- **READY --SYNC_BEGIN--> SYNCING**: Either peer may begin a sync round.
- **READY --SESSION_IDLE_TIMEOUT--> DRAINING**: Idle sessions drain instead of closing abruptly.
- **READY --HEARTBEAT_TIMEOUT--> CLOSED**: A silent peer in READY is presumed gone.
- **SYNCING --SYNC_COMPLETE--> READY**: The batch cursor is checkpointed first.
- **SYNCING --CHECKPOINT_MISMATCH--> RESYNC**: Divergent checkpoints force a resynchronization.
- **SYNCING --DELTA_CHAIN_OVERFLOW--> RESYNC**: Reported alongside ERR_DELTA_CHAIN_OVERFLOW.
- **SYNCING --HEARTBEAT_TIMEOUT--> CLOSED**: A silent peer mid-sync is presumed gone.
- **RESYNC --RESYNC_COMPLETE--> SYNCING** (guard: checkpoint verified): Streaming resumes from the verified checkpoint.
- **RESYNC --RESYNC_STALL_TIMEOUT--> CLOSED**: The node emits ERR_RESYNC_ABORTED before closing.
- **RESYNC --HEARTBEAT_TIMEOUT--> DRAINING**: Unlike READY or SYNCING, a resyncing session drains so partial replay state can be flushed to disk.
- **DRAINING --DRAIN_COMPLETE--> CLOSED**: All in-flight frames were flushed or abandoned.
- **DRAINING --OPEN_REQUEST--> DRAINING**: New work is refused while draining; the request is ignored.

A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.

Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

## 6. Frame Format

Every frame begins with a fixed header. Multi-byte integers are big-endian and unsigned. The fields appear on the wire in exactly the order of the table below.

| Field | Size (bytes) | Description |
|---|---|---|
| magic | 4 | Constant 0x4C 0x53 0x59 0x4E ('LSYN'). |
| wire_version | 2 | Big-endian unsigned; must equal the negotiated wire version. |
| flags | 2 | Bit 0 = compressed payload, bit 1 = tagged, bit 2 = checkpoint marker; other bits reserved. |
| session_id | 8 | Random 64-bit id chosen by the opening peer. |
| sequence | 8 | Monotonic per-session frame counter, starting at 1. |
| tag_length | 2 | Byte length of the tag block; 0 when the tagged flag is clear. |
| payload_length | 4 | Byte length of the payload that follows the tag block. |
| crc32 | 4 | CRC-32 (IEEE) over the header bytes preceding this field. |

The fixed header is therefore 34 bytes in total. It is followed by tag_length bytes of tag block and payload_length bytes of payload. The size of the entire encoded frame — header, tag block, and payload together — MUST NOT exceed MAX_FRAME_BYTES (262144 bytes); a peer that receives a frame declaring a larger size rejects it with error 4002 (ERR_FRAME_TOO_LARGE) without attempting to decode the payload.

Tags longer than MAX_TAG_LENGTH (48 bytes) are rejected with ERR_TAG_TOO_LONG. At most MAX_INFLIGHT_FRAMES (64) frames may be unacknowledged at any time; senders that reach the bound stall until a cumulative ACK arrives.

The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything.

## 7. Steady-State Sync and Delta Chains

In SYNCING, the sender groups deltas into batches of sync.batch_size (default 32) and expects a cumulative ACK every sync.ack_every batches. Every checkpoint.interval_deltas deltas the sender injects a checkpoint marker frame (flags bit 2). The chain of deltas since the last checkpoint may never exceed MAX_DELTA_CHAIN (512); crossing the bound raises the DELTA_CHAIN_OVERFLOW event and error 4104 (ERR_DELTA_CHAIN_OVERFLOW), and the session moves to RESYNC as specified in section 5.

Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

## 8. Resynchronization

RESYNC replays frames from the newest checkpoint both peers can verify. Replay proceeds in rounds of resync.window_frames frames (default 128, allowed range 16..1024). After at most resync.max_rounds rounds without convergence, or when a round stalls for RESYNC_STALL_TIMEOUT (30000 ms), the node abandons resynchronization with ERR_RESYNC_ABORTED (5003).

Heartbeats continue during RESYNC. Note the asymmetry called out in section 5: a HEARTBEAT_TIMEOUT during RESYNC does not close the session directly — the session drains first, so partially replayed state reaches disk and a later session can resume from it.

Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.

This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

## 9. Error Codes

Error codes travel in CLOSE and REJECT frames. Codes 1xxx are informational, 4xxx are peer errors, 5xxx are local failures.

| Code | Symbol | Meaning |
|---|---|---|
| 1000 | OK | No error; used in CLOSE frames after an orderly shutdown. |
| 4001 | ERR_MALFORMED_FRAME | The frame could not be decoded (bad magic, truncated header, or CRC mismatch). |
| 4002 | ERR_FRAME_TOO_LARGE | The declared frame size exceeds MAX_FRAME_BYTES. |
| 4003 | ERR_UNSUPPORTED_VERSION | The peer requested a wire version this node does not speak. |
| 4008 | ERR_TAG_TOO_LONG | A subscription or frame tag exceeds MAX_TAG_LENGTH bytes. |
| 4102 | ERR_CHECKPOINT_MISSING | A referenced checkpoint id is unknown to the receiving node. |
| 4104 | ERR_DELTA_CHAIN_OVERFLOW | A delta chain grew past MAX_DELTA_CHAIN without a checkpoint. |
| 5001 | ERR_INTERNAL | Unrecoverable internal failure; the session is torn down. |
| 5003 | ERR_RESYNC_ABORTED | A resynchronization round was abandoned (stall or repeated mismatch). |

- **1000 OK** — No error; used in CLOSE frames after an orderly shutdown. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.
- **4001 ERR_MALFORMED_FRAME** — The frame could not be decoded (bad magic, truncated header, or CRC mismatch). The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.
- **4002 ERR_FRAME_TOO_LARGE** — The declared frame size exceeds MAX_FRAME_BYTES. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.
- **4003 ERR_UNSUPPORTED_VERSION** — The peer requested a wire version this node does not speak. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.
- **4008 ERR_TAG_TOO_LONG** — A subscription or frame tag exceeds MAX_TAG_LENGTH bytes. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.
- **4102 ERR_CHECKPOINT_MISSING** — A referenced checkpoint id is unknown to the receiving node. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.
- **4104 ERR_DELTA_CHAIN_OVERFLOW** — A delta chain grew past MAX_DELTA_CHAIN without a checkpoint. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated.
- **5001 ERR_INTERNAL** — Unrecoverable internal failure; the session is torn down. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.
- **5003 ERR_RESYNC_ABORTED** — A resynchronization round was abandoned (stall or repeated mismatch). The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below.

When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

## 10. Configuration Parameters

Unlike the constants of sections 4 and 6, the parameters below are per-deployment tunables. Defaults are normative: a parameter left unset MUST behave exactly as its default. Ranges are inclusive at both ends; values outside the range are a configuration error and the node refuses to start.

| Parameter | Type | Default | Allowed values | Applies to |
|---|---|---|---|---|
| sync.batch_size | int | 32 | 1..256 | sender |
| sync.ack_every | int | 4 | 1..32 | receiver |
| resync.window_frames | int | 128 | 16..1024 | both |
| resync.max_rounds | int | 6 | 1..24 | both |
| heartbeat.jitter_pct | int | 10 | 0..40 | sender |
| transport.compression | enum | lz4 | none / lz4 / zstd | both |
| transport.nagle | bool | false | false / true | sender |
| checkpoint.interval_deltas | int | 256 | 32..2048 | sender |
| session.max_tags | int | 32 | 1..512 | both |
| session.reopen_backoff_ms | int | 1200 | 100..60000 | client |
| log.frame_sample_rate | int | 0 | 0..1000 | both |
| security.require_encryption | bool | true | false / true | server |

### 10.1 Parameter notes

- **sync.batch_size** — Deltas grouped into one flush before an ACK is expected. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.
- **sync.ack_every** — Batches acknowledged with a single cumulative ACK. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.
- **resync.window_frames** — Frames replayed per resync round; larger windows recover faster but hold more memory. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.
- **resync.max_rounds** — Resync rounds attempted before ERR_RESYNC_ABORTED. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.
- **heartbeat.jitter_pct** — Random jitter applied to HEARTBEAT_INTERVAL to avoid thundering herds. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.
- **transport.compression** — Codec for payloads when the compressed flag is set. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.
- **transport.nagle** — Whether small frames may be coalesced. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.
- **checkpoint.interval_deltas** — Deltas between automatic checkpoint markers; must stay below MAX_DELTA_CHAIN. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.
- **session.max_tags** — Distinct subscription tags one session may hold. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports.
- **session.reopen_backoff_ms** — Initial backoff after an unexpected CLOSED; doubles per attempt. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.
- **log.frame_sample_rate** — Per-mille of frames logged verbatim; 0 disables sampling. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.
- **security.require_encryption** — Reject peers that do not offer the encrypted-frames feature. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

## 11. Compatibility and Versioning

Protocol releases are versioned MAJOR.MINOR.PATCH. Features are negotiated at handshake time by name; a feature is usable on a session only when the client library and the server both meet the versions below. The two columns intentionally differ — client support usually ships first.

| Feature | Introduced in client | Minimum server version | Notes |
|---|---|---|---|
| encrypted-frames | 2.9.0 | 3.0.0 | Mandatory when security.require_encryption is true. |
| tag-subscriptions | 3.0.0 | 3.0.2 | Server-side tag filtering; earlier servers ignore tag blocks. |
| delta-compression | 3.1.2 | 3.1.0 | Per-delta codec negotiation inside a batch. |
| multiplexed-sessions | 3.1.0 | 3.1.4 | Several logical sessions over one transport connection. |
| partial-checkpoint | 3.2.0 | 3.2.1 | Checkpoints covering a tag subset; requires tag-subscriptions. |

Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

## 12. Worked Examples

**Example 1 — batching.** With defaults, a sender flushes after every 32 deltas and expects one cumulative ACK per 4 batches, i.e. one ACK per 128 deltas. With MAX_INFLIGHT_FRAMES = 64, at most 64 of those may be unacknowledged at once, so a default sender stalls after 2 unacknowledged batches.

**Example 2 — frame sizing.** A frame carrying a 12-byte tag and a 1000-byte payload occupies 34 + 12 + 1000 = 1046 bytes on the wire, comfortably below MAX_FRAME_BYTES (262144). A hypothetical frame declaring payload_length = 262144 would exceed the bound once the 34-byte header is added and is rejected with ERR_FRAME_TOO_LARGE (4002).

**Example 3 — resync budget.** With defaults, a resynchronization may replay up to 128 x 6 = 768 frames before ERR_RESYNC_ABORTED (5003), and each round has 30000 ms to make progress.

**Example 4 — reconnect backoff.** After an unexpected CLOSED, a default client waits 1200 ms, then 2400 ms, then 4800 ms between attempts, capping at the configured range maximum.

This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.

The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports.

*End of specification.*

## Appendix A. Implementation Notes (non-normative)

**A.1.** A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

**A.2.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.

**A.3.** A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

**A.4.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.

**A.5.** A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

**A.6.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

**A.7.** Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

**A.8.** In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports.

**A.9.** The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

**A.10.** Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

**A.11.** In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.12.** The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.13.** The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.14.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

**A.15.** Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything.

**A.16.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.17.** The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated.

**A.18.** Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

**A.19.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

**A.20.** All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions.

**A.21.** A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries.

**A.22.** This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

**A.23.** In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

**A.24.** The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.25.** All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries.

**A.26.** Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

**A.27.** Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries.

**A.28.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

**A.29.** The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

**A.30.** Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below.

**A.31.** Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt.

**A.32.** Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything.

**A.33.** All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document.

**A.34.** This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.35.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. When in doubt, implementations SHOULD prefer closing a session over guessing: LatticeSync sessions are cheap to reopen and expensive to corrupt. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

**A.36.** The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries.

**A.37.** The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict. Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later.

**A.38.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

**A.39.** Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions. This behaviour is intentionally conservative; the protocol favours predictable recovery over opportunistic throughput whenever the two conflict.

**A.40.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports.

**A.41.** Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly.

**A.42.** The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions.

**A.43.** The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below. Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly.

**A.44.** In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below.

**A.45.** Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. The v2 protocol handled this differently, and gateways translating between v2 and v3 must take care not to leak the old semantics into new sessions.

**A.46.** Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. All sizes in this document are in bytes and all durations are in milliseconds unless a unit is written out explicitly. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

**A.47.** Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. The conformance suite exercises every row of the table above with both minimal and maximal values, and additionally fuzzes the encodings at the boundaries. Readers implementing only the client side may skim this subsection, but should return to it before implementing reconnection, because the server's view of the exchange is not symmetric.

**A.48.** Conforming nodes log a structured event whenever this path is taken, carrying the session id, the current sequence number, and the wall-clock time, so operators can reconstruct the ordering later. The examples in section 12 walk through this machinery step by step with concrete numbers taken from the tables in this document. The working group revisited this decision twice during the v3 cycle and kept it both times; the rationale is recorded in the appendix of the meeting notes and summarized below.

**A.49.** In practice, deployments that ignore this rule tend to discover it during failover testing rather than code review, which is the expensive place to discover anything. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

**A.50.** Middleboxes that terminate LatticeSync MUST behave as full peers; half-proxies that forward frames without tracking state are the leading cause of interoperability reports. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time.

**A.51.** Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises. Timer wheels with coarse granularity are acceptable as long as the effective expiry never occurs earlier than the nominal value; firing late by up to ten percent is tolerated. A common implementation mistake is to enforce this check after decompression rather than before; the reference implementation enforces it on the wire representation, and the conformance suite tests exactly that.

**A.52.** Nothing in this section requires a particular threading model; single-threaded event loops and thread-per-session designs are both known to interoperate cleanly. Operators frequently ask whether these values can be raised in private deployments; they can not, because both peers derive buffer geometry from them at handshake time. Implementations MUST treat the numeric values in this section as protocol constants: they are not tunable, and peers that disagree on them will desynchronize in ways that are hard to observe until load rises.

