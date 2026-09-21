#!/usr/bin/env python3
"""Dedupe people.tsv per SPEC.md -> dedup.json."""
import json
import unicodedata


def name_key(name):
    s = unicodedata.normalize("NFKC", name)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    s = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in s)
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip().casefold()


def email_key(email):
    local, _, domain = email.rpartition("@")
    domain = unicodedata.normalize("NFKC", domain).casefold().strip()
    local = unicodedata.normalize("NFKC", local)
    local = "".join(ch for ch in local if unicodedata.category(ch) != "Cf")
    local = local.casefold()
    if domain == "mailbox.example":
        local = local.split("+", 1)[0].replace(".", "")
    return f"{local}@{domain}"


rows = []
with open("people.tsv", encoding="utf-8") as fh:
    next(fh)
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        rid, name, email = line.split("\t")
        rows.append((int(rid), name, email))

clusters = {}
for rid, name, email in rows:
    clusters.setdefault((name_key(name), email_key(email)), []).append(rid)
out = sorted([sorted(ids) for ids in clusters.values()], key=lambda c: c[0])
res = {
    "clusters": out,
    "stats": {
        "rows": len(rows),
        "clusters": len(out),
        "singletons": sum(1 for c in out if len(c) == 1),
        "merged_rows": len(rows) - len(out),
    },
}
with open("dedup.json", "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=2, sort_keys=True)
    fh.write("\n")
print(f"{res['stats']['clusters']} clusters from {res['stats']['rows']} rows")
