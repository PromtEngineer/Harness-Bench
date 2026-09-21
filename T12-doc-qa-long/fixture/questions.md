# Questions about docs/protocol-spec.md

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
