#!/usr/bin/env python3
"""Generate events.csv for T17-perf-fix. Deterministic (fixed seed)."""
import csv
import random
import sys

SEED = 170017
N_EVENTS = 80000
N_USERS = 150
VOCAB_SIZE = 300
POOL_SIZE = 40

ADJ = [
    "amber", "brisk", "coral", "dusty", "ember", "frost", "gilded", "hollow",
    "iron", "jade", "keen", "lunar", "mossy", "noble", "opal", "pale",
    "quiet", "rustic", "silver", "tidal",
]
NOUN = [
    "anchor", "beacon", "cinder", "delta", "echo", "fjord", "grove",
    "harbor", "inlet", "juniper", "knoll", "lagoon", "mesa", "nectar", "orchid",
]


def main(out_path: str) -> None:
    rng = random.Random(SEED)
    vocab = sorted(f"{a}-{n}" for a in ADJ for n in NOUN)
    assert len(vocab) == VOCAB_SIZE
    pools = [rng.sample(vocab, POOL_SIZE) for _ in range(N_USERS)]
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["event_id", "user", "tags"])
        for i in range(N_EVENTS):
            u = rng.randrange(N_USERS)
            k = rng.choices([1, 2, 3, 4], weights=[15, 40, 30, 15])[0]
            tags = rng.sample(pools[u], k)
            w.writerow([f"e{i:06d}", f"u{u:03d}", "|".join(tags)])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "events.csv")
